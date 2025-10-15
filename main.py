"""
Bluefin Auto Trader Bot
-----------------------
Automated trading bot for Bluefin Exchange (Sui Network).
Executes random LONG/SHORT TWAP-based trades and sends updates via Telegram.

Author: YusufDinanet
GitHub: https://github.com/YusufDinanet/bluefin-trade-bot
Version: 1.0
License: MIT
"""

import os
import asyncio
import random
import time
import math
import requests
from dotenv import load_dotenv
from bluefin_v2_client import (
    BluefinClient,
    Networks,
    MARKET_SYMBOLS,
    ORDER_SIDE,
    ORDER_TYPE,
    OrderSignatureRequest,
)

load_dotenv()
BOT_TOKEN       = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID         = os.getenv("TELEGRAM_CHAT_ID")
WALLET_MNEMONIC = os.getenv("WALLET_MNEMONIC")
BASE_URL        = f"https://api.telegram.org/bot{BOT_TOKEN}"

SYMBOL            = MARKET_SYMBOLS.WAL
MARGIN_USD        = 1  
TWAP_COUNT        = 5
LEVERAGE          = 5
HOLD_MIN_SEC      = 60
HOLD_MAX_SEC      = 90
WAIT_MIN_SEC      = 60
WAIT_MAX_SEC      = 90
STOP_LOSS_USD     = -0.05
TAKE_PROFIT_USD   = 0.09
CLOSE_RETRIES     = 3
CLOSE_CONFIRM_S   = 10
MAX_POSITION_SIZE = 100
TWAP_INTERVAL     = 1  # saniye

def from_base18(x: str) -> float:
    return int(x) / 1e18

def send_msg(text: str) -> int | None:
    try:
        r = requests.post(f"{BASE_URL}/sendMessage",
                          data={"chat_id": CHAT_ID, "text": text[:4000]},
                          timeout=5).json()
        return r["result"]["message_id"] if r.get("ok") else None
    except:
        return None

def edit_msg(message_id: int, text: str) -> None:
    try:
        requests.post(f"{BASE_URL}/editMessageText",
                      data={"chat_id": CHAT_ID, "message_id": message_id, "text": text[:4000]},
                      timeout=5)
    except:
        pass

async def get_current_position(client: BluefinClient):
    try:
        resp = await client.get_user_position({
            "symbol": SYMBOL, "pageSize":1, "pageNumber":1,
            "parentAddress": client.get_public_address()
        })
        if isinstance(resp, dict) and resp.get("avgEntryPrice"):
            return resp
        data = resp.get("data", resp.get("result", {}))
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            data = data["data"]
        if isinstance(data, list) and data:
            return data[0]
    except:
        pass
    acct = await client.get_user_account_data()
    for p in acct.get("result", acct).get("positions", []):
        if p.get("symbol")==SYMBOL.value and int(p.get("avgOpenPrice","0"))>0:
            return p
    return None

async def close_existing_position(client: BluefinClient, tag: str):
    prev_size = None
    not_found_count = 0
    while True:
        pos = await get_current_position(client)
        if not pos or int(pos.get("quantity", 0)) == 0:
            send_msg(f"[{tag}] ✔️ Tüm pozisyonlar KAPALI, yeni işleme geçiliyor.")
            return
        size = int(pos["quantity"]) / 1e18

        if prev_size is not None:
            if size > prev_size + 0.01:
                send_msg(f"[{tag}] 🚨 POZİSYON ANORMAL BÜYÜDÜ! ({prev_size:.4f} → {size:.4f})\nBOT DONDURULDU! Manuel kontrol et.")
                return
            elif abs(size - prev_size) < 0.01:
                send_msg(f"[{tag}] ⏳ Pozisyon değişmedi ({size:.4f}), 30s bekleniyor…")
                await asyncio.sleep(30)
                continue
            elif size < prev_size - 0.01:
                send_msg(f"[{tag}] 🔄 Pozisyon küçüldü. ({prev_size:.4f} → {size:.4f}) Kapatmaya devam...")
        prev_size = size

        side0 = pos.get("side") or pos.get("positionSide")
        close_side = ORDER_SIDE.SELL if side0 in (ORDER_SIDE.BUY, "LONG") else ORDER_SIDE.BUY

        send_msg(f"[{tag}] ⚠️ Pozisyon kapatılıyor… (size={size:.4f})")
        req = OrderSignatureRequest(
            symbol=SYMBOL, price=0, quantity=size,
            side=close_side, orderType=ORDER_TYPE.MARKET,
            leverage=LEVERAGE,
            expiration=int(time.time()*1000)+60_000
        )
        await client.post_signed_order(client.create_signed_order(req))
        await asyncio.sleep(15)

        cur = await get_current_position(client)
        if cur and int(cur.get("quantity", 0)) != 0:
            send_msg(f"[{tag}] 🔒 Force-close…")
            req = OrderSignatureRequest(
                symbol=SYMBOL, price=0, quantity=size,
                side=close_side, orderType=ORDER_TYPE.MARKET,
                leverage=LEVERAGE,
                expiration=int(time.time()*1000)+60_000
            )
            await client.post_signed_order(client.create_signed_order(req))
            await asyncio.sleep(12)
            cur2 = await get_current_position(client)
            if cur2 and int(cur2.get("quantity", 0)) != 0:
                not_found_count += 1
                send_msg(f"[{tag}] ❗️ Hâlâ açık. ({not_found_count}/{CLOSE_CONFIRM_S})")
                if not_found_count >= CLOSE_CONFIRM_S:
                    send_msg(f"[{tag}] 🚨 Kapatmada sorun var, manuel kontrol et!")
                    return
            else:
                send_msg(f"[{tag}] ✔️ Force-close: Pozisyon KAPANDI.")
                break
        else:
            send_msg(f"[{tag}] ✔️ Pozisyon kapandı.")
            break

async def open_and_close_random(client: BluefinClient, side, tag: str):
    try:
        acct = await client.get_user_account_data()
        balance = None
        if "walletBalance" in acct:
            balance = int(acct["walletBalance"]) / 1e18
        elif "result" in acct and "walletBalance" in acct["result"]:
            balance = int(acct["result"]["walletBalance"]) / 1e18
        elif "balances" in acct and acct["balances"]:
            balance = int(acct["balances"][0]["walletBalance"]) / 1e18
        send_msg(f"💼 Wallet Balance: {balance:.4f} USDC" if balance is not None else "💼 Balance alınamadı")

        await close_existing_position(client, tag)

        raw = await client.get_market_data(SYMBOL)
        data = raw.get("result", raw)
        price = next((from_base18(data[k]) for k in ("markPrice","lastPrice","price") if data.get(k)), None)
        if price is None:
            send_msg(f"[{tag}] ❌ Fiyat alınamadı, atlanıyor.")
            return

        # ==== TWAP ile slice açma (tek mesaj + edit) ====
        slice_qty = (MARGIN_USD * LEVERAGE) / price
        slice_qty = min(slice_qty, MAX_POSITION_SIZE)
        if SYMBOL == MARKET_SYMBOLS.WAL:
            slice_qty = max(1, math.floor(slice_qty))

        # Placeholder mesaj
        twap_msg_id = send_msg(f"[{tag}] 🚀 TWAP 0/{TWAP_COUNT} başlatılıyor...")

        for i in range(1, TWAP_COUNT + 1):
            # TWAP emri aç
            req = OrderSignatureRequest(
                symbol=SYMBOL, price=0, quantity=slice_qty,
                side=side, orderType=ORDER_TYPE.MARKET,
                leverage=LEVERAGE,
                expiration=int(time.time()*1000)+60_000
            )
            await client.post_signed_order(client.create_signed_order(req))

            # Aynı mesajı güncelle
            edit_msg(twap_msg_id, f"[{tag}] 🚀 TWAP {i}/{TWAP_COUNT} açıldı @ {price:.6f}")
            await asyncio.sleep(TWAP_INTERVAL)

        # TWAP tamamlandı bildirimi
        send_msg(f"[{tag}] 🚀 TWAP tamamlandı.")
        # ======================================

        opened = False
        for i in range(1, 4):
            await asyncio.sleep(10)
            if await get_current_position(client):
                send_msg(f"[{tag}] ✅ OPEN check {i}/3: açıldı.")
                opened = True
                break
            else:
                send_msg(f"[{tag}] ⚠️ OPEN check {i}/3: yok.")
        if not opened:
            send_msg(f"[{tag}] ⏳ Son 15s ekstra kontrol...")
            await asyncio.sleep(15)
            if await get_current_position(client):
                send_msg(f"[{tag}] ✅ Açıldı.")
            else:
                send_msg(f"[{tag}] ❌ Açılmadı, atlanıyor.")
                return

        pos = await get_current_position(client)
        entry_price   = int(pos["avgEntryPrice"])/1e18
        position_size = int(pos["quantity"])/1e18
        status_id = send_msg(f"[{tag}] Durum\nEntry: {entry_price:.6f}\nSize : {position_size:.6f}\nPnL  : 0.0000\nSüre : 0s")

        hold, start, last_edit = random.uniform(HOLD_MIN_SEC, HOLD_MAX_SEC), time.time(), 0
        send_msg(f"[{tag}] ⏱ Hold~{hold/60:.1f}dk; SL={STOP_LOSS_USD}, TP={TAKE_PROFIT_USD}")
        while True:
            elapsed = time.time() - start
            if elapsed >= hold:
                send_msg(f"[{tag}] ⌛ Süre bitti."); break
            cur = await get_current_position(client)
            pnl = int(cur.get("unrealizedProfit",0))/1e18 if cur else 0.0
            if status_id and time.time() - last_edit >= 10:
                edit_msg(status_id,
                    f"[{tag}] Durum\nEntry: {entry_price:.6f}\nSize : {position_size:.6f}\nPnL  : {pnl:.4f}\nSüre : {int(elapsed)}s"
                )
                last_edit = time.time()
            if pnl <= STOP_LOSS_USD:
                send_msg(f"[{tag}] ⚡️ SL (PnL={pnl:.4f})"); break
            if pnl >= TAKE_PROFIT_USD:
                send_msg(f"[{tag}] 🎯 TP (PnL={pnl:.4f})"); break
            await asyncio.sleep(1)

        close_side = ORDER_SIDE.SELL if side==ORDER_SIDE.BUY else ORDER_SIDE.BUY
        for i in range(1, CLOSE_RETRIES+1):
            send_msg(f"[{tag}] 🔄 CLOSE deneme {i}")
            req = OrderSignatureRequest(
                symbol=SYMBOL, price=0, quantity=position_size,
                side=close_side, orderType=ORDER_TYPE.MARKET,
                leverage=LEVERAGE,
                expiration=int(time.time()*1000)+60_000
            )
            await client.post_signed_order(client.create_signed_order(req))
            await asyncio.sleep(12)
            if not await get_current_position(client):
                send_msg(f"[{tag}] ✅ Kapandı."); break
            else:
                send_msg(f"[{tag}] ⚠️ Hâlâ açık (try {i}).")
        else:
            send_msg(f"[{tag}] 🔒 Force-close…")
            req = OrderSignatureRequest(
                symbol=SYMBOL, price=0, quantity=position_size,
                side=close_side, orderType=ORDER_TYPE.MARKET,
                leverage=LEVERAGE,
                expiration=int(time.time()*1000)+60_000
            )
            await client.post_signed_order(client.create_signed_order(req))
            await asyncio.sleep(12)
            if not await get_current_position(client):
                send_msg(f"[{tag}] ✔️ Force-close: KAPANDI.")
            else:
                send_msg(f"[{tag}] 🚨 Manuel kontrol et!")

        total = time.time() - start
        nxt   = random.uniform(WAIT_MIN_SEC, WAIT_MAX_SEC)
        send_msg(f"[{tag}] ✅ DONE | Süre: {total/60:.1f}dk | Next: {nxt:.1f}s")
        await asyncio.sleep(nxt)

    except Exception as e:
        send_msg(f"[{tag}] 🚨 HATA: {e}. Devam ediliyor.")
        await asyncio.sleep(5)

async def main():
    client = BluefinClient(True, Networks["SUI_PROD"], WALLET_MNEMONIC)
    await client.init(True)
    send_msg("🤖 Bot başlatıldı!")
    while True:
        side, tag = random.choice([(ORDER_SIDE.BUY, "LONG"), (ORDER_SIDE.SELL, "SHORT")])
        await open_and_close_random(client, side, tag)

if __name__ == "__main__":
    asyncio.run(main())
