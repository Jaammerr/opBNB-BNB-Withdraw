# 🌐 BNB > opBNB Sender via GasZip [v1.0]

<div align="center">
  
  <p align="center">
    <a href="https://t.me/JamBitPY">
      <img src="https://img.shields.io/badge/Telegram-Channel-blue?style=for-the-badge&logo=telegram" alt="Telegram Channel">
    </a>
    <a href="https://t.me/JamBitChat">
      <img src="https://img.shields.io/badge/Telegram-Chat-blue?style=for-the-badge&logo=telegram" alt="Telegram Chat">
    </a>
  </p>

</div>


## 🛠️ Installation

1. **Clone the Repository**
   ```bash
   git clone [repository URL]
   ```

2. **Set Up Virtual Environment**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows
   source venv/bin/activate      # Unix/MacOS
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 📝 Input Files Structure

### 📁data/target_addresses.txt

```plaintext
evm_address1
evm_address2
```
###

### 📁 data/proxies.txt
```
http://user:pass@ip:port
http://ip:port:user:pass
http://user:pass:ip:port
```


## 📊 Results

```plaintext
📁 results/sender/
  ├── 📄 bridge_success.txt  # Successful bridge wallet addresses
  ├── 📄 bridge_failed.txt  # Failed bridge wallet addresses
  ```

## 🚀 Usage


1. Configure your settings in settings.yaml
2. Add your accounts to target_addresses.txt
3. Add proxies to proxies.txt
4. Run the checker:
   ```bash
   python run.py
   ```
