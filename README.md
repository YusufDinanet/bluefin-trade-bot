# 🦈 Bluefin Auto Trader Bot

An automated trading bot for **Bluefin Exchange (Sui Network)**.  
It continuously opens and closes TWAP-based trades to **generate trading fees** and climb higher in Bluefin’s **reward pool leaderboard**.

---

## 🎯 Purpose

The main purpose of this bot is **fee farming** — continuously trading to spend as many fees as possible.  
The more trading volume you generate, the more rewards you earn from Bluefin’s reward pool.  

The bot automatically:
- Opens randomized **LONG/SHORT** trades  
- Controls trade size and exposure  
- Closes positions automatically based on TP/SL or time  
- Sends live Telegram notifications for every event  

---

## ⚙️ Features

- ✅ Fully automated trading loop  
- 🔁 Random LONG/SHORT trades with TWAP slicing  
- 💬 Real-time Telegram alerts (PnL, status, errors, etc.)  
- ⚡ Stop-Loss & Take-Profit system  
- 🧠 Smart position management (no overlapping trades)  
- ☁️ AWS EC2-ready for 24/7 uptime  

---

## 📁 Project Structure

```
bluefin-trade-bot/
│
├── main.py             # Core trading logic
├── .env.example        # Example environment variables
├── .gitignore          # Keeps secrets private
├── requirements.txt     # Dependencies
└── README.md           # Documentation
```

---

## 🔐 Environment Variables

Create a file named `.env` in the same directory as `main.py`.  
Use `.env.example` as a reference:

```bash
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"
WALLET_MNEMONIC="YOUR_12_WORD_MNEMONIC"
```

⚠️ **Never upload `.env` to GitHub!**  
It contains sensitive wallet and API credentials.

---

## 🧮 Strategy & Parameters

All key strategy parameters are defined inside `main.py`.

| Parameter | Description | Default |
|------------|-------------|----------|
| `SYMBOL` | Market pair traded (e.g., `MARKET_SYMBOLS.WAL`) | WAL |
| `MARGIN_USD` | USD margin used per trade | 1 |
| `TWAP_COUNT` | Number of TWAP slices per trade | 5 |
| `LEVERAGE` | Leverage applied | 5 |
| `HOLD_MIN_SEC` | Minimum time to hold a position | 60 |
| `HOLD_MAX_SEC` | Maximum time to hold a position | 90 |
| `WAIT_MIN_SEC` | Minimum wait before next trade | 60 |
| `WAIT_MAX_SEC` | Maximum wait before next trade | 90 |
| `STOP_LOSS_USD` | Stop loss (in USD) | -0.05 |
| `TAKE_PROFIT_USD` | Take profit (in USD) | 0.09 |
| `CLOSE_RETRIES` | Retry attempts when closing | 3 |
| `CLOSE_CONFIRM_S` | Confirmation attempts before alert | 10 |
| `MAX_POSITION_SIZE` | Maximum allowed open size | 100 |
| `TWAP_INTERVAL` | Delay between TWAP orders (seconds) | 1 |

---

## 📊 How the Strategy Works

### 1️⃣ Direction Selection
At the start of each cycle, the bot randomly selects whether to go **LONG** or **SHORT**.

### 2️⃣ Position Control
If there’s already an open trade, it closes it first.  
No overlapping trades are allowed — this prevents risk stacking.

### 3️⃣ TWAP Execution
TWAP (Time-Weighted Average Price) splits a large order into smaller ones over time.  
This bot uses TWAP to:
- Simulate natural trading activity  
- Trigger more trades → generate more **fees**  
- Avoid big slippage or one-shot orders  

Example:  
If `TWAP_COUNT = 5` and `TWAP_INTERVAL = 1`,  
the bot opens 5 mini-orders, one every 1 second.

### 4️⃣ Holding Period
Once opened, the position is held for a random duration between `HOLD_MIN_SEC` and `HOLD_MAX_SEC`.

### 5️⃣ TP / SL Logic
While the position is open, the bot tracks **unrealized PnL**:
- If `TAKE_PROFIT_USD` reached → closes for profit  
- If `STOP_LOSS_USD` reached → closes to cut loss  
- If neither hit → closes after hold timer ends  

### 6️⃣ Safe Exit
When closing, it retries up to `CLOSE_RETRIES` times.  
If still open after `CLOSE_CONFIRM_S` seconds, it sends a manual warning via Telegram.

### 7️⃣ Cooldown
After closing, the bot waits a random time between `WAIT_MIN_SEC`–`WAIT_MAX_SEC` before restarting.

This infinite loop creates continuous fee activity — ideal for **Bluefin reward farming**.

---

## 💬 Telegram Integration

Every major event is sent to your Telegram chat in real time:
- 🔔 Bot started / stopped  
- 🟢 Position opened (direction, entry price, size)  
- 📈 PnL updates  
- 🎯 TP / ⚡ SL triggered  
- ❌ Errors and recovery alerts  

### Setup Steps

1. Create a Telegram bot via [@BotFather](https://t.me/BotFather).  
2. Get your **Bot Token**.  
3. Find your **Chat ID** (using any “get chat id” bot).  
4. Add them to `.env`.  
5. Run the bot — you’ll start getting live messages.

---

## 🧩 Installation & Usage

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/bluefin-trade-bot.git
cd bluefin-trade-bot
```

### 2️⃣ Install Requirements
```bash
pip install -r requirements.txt
```

### 3️⃣ Create `.env`
```bash
cp .env.example .env
nano .env
```

### 4️⃣ Run the Bot
```bash
python main.py
```

Once running, the bot continuously trades and sends updates to Telegram.

---

## ☁️ Deploying on AWS EC2 (Free Tier)

You can host the bot **24/7 for free** using Amazon AWS.

### Step-by-Step Setup (Real Tested Process)

1. **Create a Free AWS Account**
   - Visit [aws.amazon.com/free](https://aws.amazon.com/free)
   - Activate the Free Tier plan.

2. **Launch an EC2 Instance**
   - Choose **Ubuntu Server 22.04 LTS**
   - Select the free type `t2.micro`
   - Generate and download a `.pem` key

3. **Connect via PuTTY**
   - Convert your `.pem` to `.ppk` (if needed)
   - Open PuTTY and connect:
     ```
     ubuntu@<your-instance-ip>
     ```

4. **Transfer Files Using FileZilla**
   - Protocol: SFTP  
   - Host: your EC2 IP  
   - Username: ubuntu  
   - Key: your `.ppk` file  
   - Upload project files (`main.py`, `.env`, etc.)

5. **Install Python & Dependencies**
   ```bash
   sudo apt update && sudo apt install python3-pip -y
   pip install -r requirements.txt
   ```

6. **Start the Bot (Run in Background)**
   ```bash
   nohup python3 main.py > bot.log 2>&1 &
   ```
   - Keeps running even if you close PuTTY.  
   - Logs are saved in `bot.log`.

7. **Monitor the Bot**
   ```bash
   tail -f bot.log
   ```

8. **Stop the Bot**
   ```bash
   pkill -f main.py
   ```

💡 *This setup creates a 24/7 running environment using AWS’s free EC2 service.*

---

## ⚠️ Disclaimer

This project is **for educational and experimental purposes only.**  
Crypto trading involves financial risk.  
The goal of this bot is **fee generation**, not guaranteed profit.  
Use with small amounts and always protect your wallet mnemonic.

---

## 🧭 Future Plans

- Dynamic fee optimization based on volume  
- Multi-symbol market support (WAL, SUI, BLUE, etc.)  
- Telegram control commands (`/pause`, `/status`, `/stop`)  
- Cloud analytics dashboard  