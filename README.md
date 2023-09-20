# How to run  
### Requirements  
- a telegram bot token  
  - visit <a href=https://t.me/botfather>botfather</a> to create a new bot and save its token  
  - define an environment variable called `NABAAT_BOT_TOKEN` with your bot token  
- mongodb  
  - after installing mongodb, you need to define an environment variable called `MONGODB_URI` and assign it `mongodb://127.0.0.1:27017`  
- install dependencies  
  - `pip install -r requirements.txt`  
### Entry script
move to the project directory and run `python3 nabaat_bot/main.py`