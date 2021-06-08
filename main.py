import discord
from discord.ext import tasks, commands
from gtts import gTTS
from sys import getsizeof

client = commands.Bot(command_prefix='$')

speakers = {}
allowed_users = [241993159381483531, 207625855697027083]


class Server:
    server_dict = {}

    def __init__(self, speaker, voice_client, input_channel):
        self.speaker = speaker
        self.input_channel = input_channel
        self.voice_client = voice_client
        self.queue = []
    
    def update_queue(self):
        if len(self.queue) > 0:
            msg = self.queue.pop(0)
            tts = gTTS(text=msg, lang='en', slow=False, tld='ca')
            tts.save('tts.mp3')
            audio_source = discord.FFmpegPCMAudio('tts.mp3')
            self.voice_client.play(audio_source, after=lambda a: self.update_queue())
    
    def add_queue(self, msg):
        if type(msg) == str and 0 < len(msg) < 350:
            if msg.startswith('<a:') or msg.startswith('<:'):
                msg = msg.split(':')[1]
            self.queue.append(msg)
    
    @classmethod
    def new_tts(cls, server_id, voice_client, speaker, input_channel):
        cls.server_dict[server_id] = cls(speaker, voice_client, input_channel)


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


@client.event
async def on_message(message):
    if message.author.id == client.user.id:
        return

    if message.content.startswith('$'):
        await client.process_commands(message)
        return

    if message.guild.id in Server.server_dict:
        server = Server.server_dict[message.guild.id]
        if message.author.id == server.speaker and message.channel.id == server.input_channel:
            server.add_queue(message.content)
            if not server.voice_client.is_playing():
                server.update_queue()


@client.event
async def on_voice_state_update(member, before, after):
    if member.id == client.user.id:
        return

    if member.guild.id in Server.server_dict:
        server = Server.server_dict[member.guild.id]
        if server.speaker == member.id and after.channel == None:
            await server.voice_client.disconnect()
            server.speaker = None
            await client.get_channel(server.input_channel).send('User Disconnected: TTS is off')


@client.command(pass_context=True)
async def tts(ctx, state):
    if state == 'on':
    # if state == 'on' and ctx.message.author.id in allowed_users:
        if ctx.message.author.voice == None:
            await ctx.message.channel.send('You are not in a voice channel')
        elif not ctx.voice_client:
            channel = ctx.message.author.voice.channel
            await channel.connect()

            await ctx.message.channel.send('TTS is on')

            if ctx.message.guild.id in Server.server_dict:
                server = Server.server_dict[ctx.message.guild.id]
                server.speaker = ctx.message.author.id
                server.voice_client = ctx.voice_client
                server.input_channel = ctx.channel.id
            else:
                Server.new_tts(ctx.message.guild.id, ctx.voice_client, ctx.message.author.id, ctx.channel.id)

            server = Server.server_dict[ctx.message.guild.id]
            server.add_queue(f'{ctx.message.author.name} has activated tts')
            server.update_queue()


    elif state == 'off' and ctx.message.author.id == Server.server_dict[ctx.message.guild.id].speaker:
        if ctx.voice_client:
            await ctx.voice_client.disconnect()

            await ctx.message.channel.send('TTS is off')

            Server.server_dict[ctx.message.guild.id].speaker = None


with open('secrets.txt', 'r') as f:
    token = int(f.readline())

client.run(token)
