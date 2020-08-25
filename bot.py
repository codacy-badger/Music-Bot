import discord
import asyncio
import aiohttp

import os
import json
import youtube_dl
import pymysql

from bs4 import BeautifulSoup
from urllib import parse 

directory = os.path.dirname(os.path.abspath(__file__)).replace("\\","/")
db_f = open(directory + "/Data/bot_info.json",mode='r')
db = db_f.read()
db_f.close()
db_json = json.loads(db)

db_ip = db_json["mysql"]["ip"]
db_user = db_json["mysql"]["user"]
db_pw = db_json["mysql"]["password"]
db_name = db_json["mysql"]["database"]

connect = pymysql.connect(host=db_ip, user=db_user, password=db_pw,db=db_name, charset='utf8') #클라이언트 API키 불러오기.
cur = connect.cursor()
cur.execute("SELECT * from Music_Bot")
client_list = cur.fetchone()
key = client_list[0]
token = client_list[1]
connect.close()

client = discord.Client()
voice_channels = {}
ydl_opts  = {
    'format': 'bestaudio/bestaudio'
}

def get_voice(message):
    count = len(client.voice_clients)
    for i in range(count):
        guildID =  client.voice_clients[i].guild.id
        if guildID == message.guild.id:
            return client.voice_clients[i]
    return None

def download(video_id,link):
    if not os.path.isfile(f'{directory}/{video_id}.mp3'):
        ydl_opts_cache = ydl_opts
        ydl_opts_cache['outtmpl'] = f'{directory}/Music_cache/{video_id}.mp3'
        with youtube_dl.YoutubeDL(ydl_opts_cache) as ydl:
            ydl.download([link])

def f_thumbnail(video):
    try:
        thumbnail = video['snippet']['thumbnails']['default']['url']
    except KeyError:
        try:
            thumbnail = video['snippet']['thumbnails']['high']['url']
        except KeyError:
            thumbnail = video['snippet']['thumbnails']['medium']['url']
    finally:
        return thumbnail

async def playlist(voiceC,playlistId,author):
    params = {
        "part":"snippet",
        "key":key,
        "playlistId":playlistId
    }
    def append_channel(html,author):
        for i in html['items']:
            video_id = i['snippet']['resourceId']['videoId']
            title = i['snippet']['title']
            thumbnail = f_thumbnail(i)
            download(video_id,f'https://www.youtube.com/watch?v={video_id}')
            voice_channels[voiceC].append((video_id,title,author,thumbnail))
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://www.googleapis.com/youtube/v3/playlistItems",params=params) as resp:
            html = await resp.json()
    append_channel(html,author)
    while "nextPageToken" in html:
        params['pageToken'] = html['nextPageToken']
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://www.googleapis.com/youtube/v3/playlistItems",params=params) as resp:
                html = await resp.json()
        append_channel(html,author)

@client.event
async def on_ready(): 
    print("디스코드 봇 로그인이 완료되었습니다.")
    print("디스코드봇 이름:" + client.user.name)
    print("디스코드봇 ID:" + str(client.user.id))
    print("디스코드봇 버전:" + str(discord.__version__))
    print('------')
    
    answer = ""
    total = 0
    for i in range(len(client.guilds)):
        answer = answer + str(i+1) + "번째: " + str(client.guilds[i]) + "(" + str(client.guilds[i].id) + "):"+ str(len(client.guilds[i].members)) +"명\n"
        total += len(client.guilds[i].members)
    print(f"방목록: \n{answer}\n방의 종합 멤버:{total}명")

    await client.change_presence(status=discord.Status.online, activity=discord.Game("노래를 듣고싶다고? $도움를 입력하세요!"))
 
@client.event
async def on_message(message):
    author_id = message.author.mention.replace("<@","",).replace(">","").replace("!","")
    list_message = message.content.split(' ')
    prefix = '$'
    if message.content == f'{prefix}도움' or message.content == f'{prefix}도움말' or message.content == f'{prefix}help' or message.content == f'{prefix}명령어':
        embed = discord.Embed(color=0x0080ff)
        embed.set_author(icon_url=client.user.avatar_url,name='Music Bot')
        embed.add_field(name=f'음악',value='join,leave,play,skip,volume,pause,resume')
        embed.add_field(name=f'관리',value='help,ping')
        await message.channel.send(embed=embed)
        return
    if message.content == f'{prefix}join':
        if message.author.voice == None:
            embed = discord.Embed(title="MusicBot!",description=f"음성방에 들어가주세요!", color=0xaa0000)
            await message.channel.send(embed=embed)
            return
        channel = message.author.voice.channel
        voice = await channel.connect()
        voice_channels[voice] = []
        embed = discord.Embed(title="MusicBot!",description=f"{voice.channel}에 성공적으로 연결하였습니다!", color=0x0080ff)
        await message.channel.send(embed=embed)
        return
    if message.content == f'{prefix}debug':
        voiceC = get_voice(message)
        if voiceC == None:
            embed = discord.Embed(title="MusicBot!",description=f"None", color=0x0080ff)
            await message.channel.send(embed=embed)
            return
        elif voiceC in voice_channels:
            embed = discord.Embed(title="MusicBot!",description=f"{voiceC.channel.name}({voiceC.channel.id}):{voice_channels[voiceC]}", color=0x0080ff)
            await message.channel.send(embed=embed)
            return
        embed = discord.Embed(title="MusicBot!",description=f"None", color=0x0080ff)
        await message.channel.send(embed=embed)
        return
    if message.content == f'{prefix}leave':
        voiceC = get_voice(message)
        if voiceC == None or not voiceC in voice_channels:
            embed = discord.Embed(title="MusicBot!",description=f"음성채널방에 들어가있지 않습니다.", color=0xaa0000)
            await message.channel.send(embed=embed)
            return
        await voiceC.disconnect()
        embed = discord.Embed(title="MusicBot!",description=f"{voiceC.channel}에 성공적으로 떠났습니다!", color=0x0080ff)
        await message.channel.send(embed=embed)
        return
    if message.content.startswith(f'{prefix}play'):
        voiceC = get_voice(message)
        if voiceC == None or not voiceC in voice_channels:
            embed = discord.Embed(title="MusicBot!",description=f"음성채널방에 들어가있지 않습니다.", color=0xaa0000)
            await message.channel.send(embed=embed)
            return
        if len(list_message) < 2:
            embed = discord.Embed(title="MusicBot!",description=f"URL 혹은 영상 링크를 넣어주세요.", color=0xaa0000)
            await message.channel.send(embed=embed)
            return
        music = " ".join(list_message[1:])
        url_T = parse.urlparse(music)
        playlist_bool = False
        if url_T.netloc.endswith('youtube.com'):
            for i in url_T.query.split('&'):
                if i.startswith('list='):
                    embed = discord.Embed(title="MusicBot!",description=f"재생목록을 다운로드받고 있습니다.\n상황에 따라 시간이 길게 소요될 수 있으니, 양해부탁드립니다.", color=0x0080ff)
                    await message.channel.send(embed=embed)
                    music = music.replace(i,'')
                    await playlist(voiceC,i.split('list=')[1],message.author)
                    playlist_bool = True
        if not playlist_bool:
            params = {
                "part":"snippet",
                "type":"vidoe",
                "maxResults":1,
                "key":key,
                "q":music
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://www.googleapis.com/youtube/v3/search",params=params) as resp:
                    html = await resp.json()
            if len(html['items']) == 0:
                embed = discord.Embed(title="MusicBot!",description=f"검색결과가 없습니다..", color=0xaa0000)
                await message.channel.send(embed=embed)
                return
            video = html['items'][0]
            video_id = video['id']['videoId']
            title = video['snippet']['title']
            thumbnail = f_thumbnail(video)
            author = message.author
            download(video_id,f'https://www.youtube.com/watch?v={video_id}')
            voice_channels[voiceC].append((video_id,title,author,thumbnail))
        
client.run(token)
