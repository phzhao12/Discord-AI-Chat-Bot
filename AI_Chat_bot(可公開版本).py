"""
Discord AI Chat Bot
版本號碼 :V1.0
創建日期 : 2025/05/03
完成日期 : 2025/05/20
更新內容：無
"""
import discord
import asyncio  #clean inactive user's chat history will use this module
from datetime import datetime,timedelta  #print time log and check inactive user's chat
import requests  #call Groq API

#Initalize API key and model information
Groq_api_key= '<Your Groq API Key>'
DiscordBot_api_key= '<Your DiscordBot API Key>'
model_list = [
    [ 'llama-3.3-70b-versatile', 32768 ],
    [ 'deepseek-r1-distill-llama-70b', 131072 ],
    [ 'qwen-qwq-32b', 131072 ],
    [ 'meta-llama/llama-4-maverick-17b-128e-instruct', 8192 ],
    [ 'meta-llama/llama-4-scout-17b-16e-instruct', 8192 ]
]
model_names = [model[0] for model in model_list]  #slash command: /change_model will use this list
model_now = model_list[0][0]  #the default model is the first model in model_list, you can change it by using /change_model command
max_tokens = model_list[0][1]  #the default max_tokens is the first model's max_tokens, you can change it by using /change_model command
data = {} #all user's chat history will be stored in this dictionary
#set up intents
intents = discord.Intents(guilds=True)
bot = discord.Bot(intents=intents)

#call Groq API by requests module, messages is user's chat history
def call_groq_api(messages):
    url = 'https://api.groq.com/openai/v1/chat/completions'
    headers = {'Authorization': f'Bearer {Groq_api_key}','Content-Type': 'application/json'}
    payload = {'model': model_now,'messages': messages,'temperature': 0.6,'max_tokens': max_tokens}
    try:
        with requests.post(url, headers=headers, json=payload) as response:
            response.raise_for_status()  #if http status code is not 200, raise an exception
            return response.json()['choices'][0]['message']['content']
    #Exception handling
    except requests.exceptions.ConnectionError:
        print('Network connection error')
        return 'Network connection error, please check your internet connection'
    except requests.exceptions.Timeout:
        print('Request timeout')
        return 'API request timeout, please try again later'
    except requests.exceptions.HTTPError as e:
        print(f'HTTP error{e}')
        return 'HTTP error'
    except Exception as e:
        print(f'Unexpected error: {e}')
        return 'Unexpected error'

#check inactive user's chat history every 3600 seconds(1 hour) and delete them if they have been inactive for more than 2 hours.
#this function will be called by asyncio.create_task() and will run in a background thread.
async def chat_history_auto_cleaner():
    while True:
        await asyncio.sleep(3600)
        time_now = datetime.now()
        print(f'{time_now} Checking Inactive User History...')
        cutoff_time = time_now - timedelta(hours=2)
        #make a copy of data avoid modifying the original data while iterating through it
        inactive_user = []
        for guild_id, users in data.items():
            for user_id, user_data in users.items():
                if user_data['last_active'] < cutoff_time:
                    inactive_user.append((guild_id, user_id))
                    print(f'{time_now} User {user_data['display_name']} in guild {user_data['guild_name']} has been inactive for more than 2 hours.')
        #delete inactive user's chat history from data dictionary
        for guild_id, user_id in inactive_user:
            del data[guild_id][user_id]
            if not data[guild_id]:
                del data[guild_id]
        print(f'{time_now} Inactive User History Cleaned.')

#console command handler, this function will be called by asyncio.create_task() and will run in a background thread.
#close bot when user enter 'exit' in console.
async def console_command_handler():
    while True:
        command = await asyncio.to_thread(input, '>>> ')
        command = command.strip()
        if 'exit' in command:
            print('Detected the exit command, closing bot.')
            await bot.close()
        else:
            print(f'Unrecognized command: {command}, please try again.')

#generate a multi-line input interface in discord. this interface pops up when a user uses the /set_data command.
class SetData(discord.ui.Modal):
    #set up a modal interface
    def __init__(self):
        super().__init__(title='輸入資料')
        self.add_item(discord.ui.InputText(label='填寫你希望AI使用的參考資料',placeholder='例：請依照這份天氣資料回應+你的資料',style=discord.InputTextStyle.long))
    #when user click submit button, this function will be called
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        system_prompt = self.children[0].value
        #check if the user has data already
        if interaction.guild.id in data and interaction.user.id in data[interaction.guild.id]:
            data[interaction.guild.id][interaction.user.id]['last_active'] = datetime.now()
            data[interaction.guild.id][interaction.user.id]['chat_history'].append({'role': 'system', 'content': system_prompt})
        else:
            data.setdefault(interaction.guild.id, {}).setdefault(interaction.user.id, {
                'display_name': interaction.user.display_name,
                'last_active': datetime.now(),
                'chat_history': [{'role': 'system', 'content': system_prompt}],
                'guild_name': interaction.guild.name
            })
        response = f'已設定AI要參考的資料：\n{system_prompt}'
        if len(response) > 1900:
            for i in range(0, len(response), 1900):
                await interaction.followup.send(response[i:i+1900])
        else:
            await interaction.followup.send(response)
        print(f'{datetime.now()} [{interaction.guild.name}] - [{interaction.user.display_name}]\'s Preset data has been added')

@bot.event
async def on_ready():
    print(f'{datetime.now()} ☑ AI Chat Bot is now online, identifier {bot.user}')
    print(f'{datetime.now()} ☑ Joined the following servers:')
    for guild in bot.guilds:
        print(f'{datetime.now()} ☺ {guild.name}（ID: {guild.id}）')
    print(f'{datetime.now()}')
    await bot.sync_commands()
    print(f'{datetime.now()} ☑ slash commands synced')
    bot.loop.create_task(chat_history_auto_cleaner())
    print(f'{datetime.now()} ☑ Chat history auto cleaner activated')
    bot.loop.create_task(console_command_handler())
    print(f'{datetime.now()} ☑ console command handler activated')

@bot.slash_command(name='ask_ai', description='提出你的問題')
async def ask_ai(ctx: discord.ApplicationContext, question: str):
    await ctx.defer()
    print(f'{datetime.now()} [{ctx.guild.name}] - [{ctx.author.display_name}] used command /ask_ai')
    #check if the user has data already
    if ctx.guild.id in data and ctx.author.id in data[ctx.guild.id]:
        data[ctx.guild.id][ctx.author.id]['last_active'] = datetime.now()
        data[ctx.guild.id][ctx.author.id]['chat_history'].append({"role": "user", "content": question})
    else:
        data.setdefault(ctx.guild.id, {}).setdefault(ctx.author.id, {
            'display_name': ctx.author.display_name,
            'last_active': datetime.now(),
            'chat_history': [{'role': 'user', 'content': '請用台灣人習慣的中文回應，我的問題是：'+question}],
            'guild_name': ctx.guild.name
        })
    #call Groq API and get response
    response = call_groq_api(data[ctx.guild.id][ctx.author.id]['chat_history'])
    data[ctx.guild.id][ctx.author.id]['chat_history'].append({"role": "assistant", "content": response})
    #if response too long, split it into multiple messages and send them one by one
    response = 'Q: \n'+question+'\nA: \n'+response
    if len(response) > 1900:
        for i in range(0, len(response), 1900):
            await ctx.followup.send(response[i:i+1900])
    else:
        await ctx.followup.send(response)
    print(f'{datetime.now()} [{ctx.guild.name}] - [{ctx.author.display_name}]\'s reply has been sent')

@bot.slash_command(name='set_data', description='輸入給AI參考的資料(Ex：程式碼)')
async def set_data(ctx: discord.ApplicationContext):
    print(f'{datetime.now()} [{ctx.guild.name}] - [{ctx.author.display_name}] used command /set_data')
    await ctx.send_modal(SetData())

@bot.slash_command(name='clear_memory', description='清除對話紀錄&參考資料')
async def clear_memory(ctx: discord.ApplicationContext):
    await ctx.defer()
    print(f'{datetime.now()} [{ctx.guild.name}] - [{ctx.author.display_name}] used command /clear_memory')
    if ctx.guild.id in data and ctx.author.id in data[ctx.guild.id]:
        del data[ctx.guild.id][ctx.author.id]
        if not data[ctx.guild.id]:
            del data[ctx.guild.id]
        await ctx.followup.send(f'已清除[{ctx.guild.name}] - [{ctx.author.display_name}]的對話紀錄')
    else:
        await ctx.followup.send(f'查無[{ctx.guild.name}] - [{ctx.author.display_name}]的對話紀錄')

@bot.slash_command(name='model_info', description='顯示當前使用模型的資訊')
async def model_info(ctx: discord.ApplicationContext):
    await ctx.defer()
    print(f'{datetime.now()} [{ctx.guild.name}] - [{ctx.author.display_name}] used command /model_info')
    await ctx.followup.send(f'Model Name: `{model_now}`\nMax Tokens: {max_tokens}\n')

@bot.slash_command(name='available_models', description='顯示當前可切換的模型列表')
async def available_models(ctx: discord.ApplicationContext):
    await ctx.defer()
    print(f'{datetime.now()} [{ctx.guild.name}] - [{ctx.author.display_name}] used command /model_list')
    response = '### 可用的模型如下:\n\n'
    for name,tokens in model_list:
        response += f'`{name}`  (Max Tokens: {tokens})\n'
    await ctx.followup.send(response)

@bot.slash_command(name='change_model', description='切換使用的模型')
async def change_model(ctx: discord.ApplicationContext, model: discord.Option(str, choices=model_names)):
    await ctx.defer()
    print(f'{datetime.now()} [{ctx.guild.name}] - [{ctx.author.display_name}] used command /change_model')
    global model_now, max_tokens
    model_now = model
    for model_name, max_tokens in model_list:
        if model_name == model:
            max_tokens = max_tokens
            break
    await ctx.followup.send(f'已將模型切換為： {model}')

@bot.slash_command(name='get_help', description='顯示使用說明')
async def get_help(ctx: discord.ApplicationContext):
    await ctx.defer()
    print(f'{datetime.now()} [{ctx.guild.name}] - [{ctx.author.display_name}] used command /help')
    response = """
## Discord AI Chat Bot

### 可用的命令:
`/ask_ai          `    -- 輸入你要問的問題
`/set_data        `    -- 設定模型要參考的資料(可多行輸入)
`/clear_memory    `    -- 清除對話紀錄&參考資料
`/model_info      `    -- 顯示當前使用模型的資訊
`/available_models`    -- 顯示當前可切換的模型列表
`/change_model    `    -- 切換使用的模型
`/get_help        `    -- 顯示使用說明

### 一些小提示:
1. 如果你有多行資料要問AI，可以先使用`/set_data`輸入完，再使用`/ask_ai`提出問題。
2. 你不太需要手動清除對話紀錄，閒置超過兩小時的對話紀錄會被自動清除。
"""
    await ctx.followup.send(response)

#run the bot
#if you want to stop this program and make the bot offline safely, just type 'exit'.
bot.run(DiscordBot_api_key)
input("AI Chat Bot is now offline. Press Enter to exit...")
