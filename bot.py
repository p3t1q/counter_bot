from typing import List
import re
import logging
import sys
from os import environ as env

import discord
from discord.ext import commands

from src.db import get_conn, run_sql, close_conn

log_handler = logging.StreamHandler()

log = logging.getLogger()
log.setLevel(logging.DEBUG)
log.addFilter(log_handler)

# expects arg to curry to be the last of positional
def curry(function, *args, **kwargs):
    return lambda arg: function(*args, arg, **kwargs)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

def counter_name_normalization(name: str) -> str:
    return name.lower()

conn = get_conn()

def counter_exists(counter_name: str) -> bool:
    query = "SELECT EXISTS (SELECT 1 FROM counters WHERE label = %s)"
    return run_sql(conn.cursor(), query, (counter_name,))[0][0]

def is_owner_of_counter(user: int, counter_name: str) -> bool:
    query = "SELECT EXISTS (SELECT 1 FROM counters WHERE author = %s AND label = %s)"
    return run_sql(conn.cursor(), query, (user, counter_name))[0][0]

def get_current_counter_value(counter_name: str) -> int:
    counter_id = get_counter_id(counter_name)
    query = "SELECT COALESCE(SUM(amount), 0) FROM counter_updates WHERE counter_id = %s"
    return run_sql(conn.cursor(), query, (counter_id,))[0][0]

def get_counter_id(counter_name: str) -> str:
    query = "SELECT id FROM counters WHERE label = %s"
    return run_sql(conn.cursor(), query, (counter_name,))[0][0]

def update_counter_by_amount(author: int, counter_name: str, amount: int) -> bool:
    counter_id = get_counter_id(counter_name)
    query = "INSERT INTO counter_updates (author, \"counter_id\", amount) VALUES (%s, %s, %s); COMMIT;"
    try:
        run_sql(conn.cursor(), query, (author, counter_id, amount))
    except:
        return False

    return True

def create_counter(user_owner: int, counter_name: str):
    query = "INSERT INTO counters (author, label) VALUES (%s, %s); COMMIT;"
    run_sql(conn.cursor(), query, (user_owner, counter_name))

def user_owned_counters(user_owner: int) -> List[str]:
    query = "SELECT label from counters WHERE author = %s"
    ret = run_sql(conn.cursor(), query, (user_owner,))
    return [counter[0] for counter in ret]


@bot.command()
async def citace(ctx):
    counters = user_owned_counters(ctx.author.id)
    message = "\n".join(f"{counter} = {get_current_counter_value(counter)}" for counter in counters)
    if message:
        await ctx.reply(message)
    else:
        await ctx.reply("No counters.")

@bot.command()
async def citac(ctx, counter_name: str):
    counter_name = counter_name_normalization(counter_name)
    if counter_exists(counter_name):
        current_value = get_current_counter_value(counter_name)
        await ctx.reply(f"{counter_name} = {current_value}")
        return
        
    await ctx.reply(f"Counter \"{counter_name}\" doesn't exist.")


@bot.command()
async def counter_create(ctx, counter_name:str):
    counter_name = counter_name_normalization(counter_name)
    if counter_exists(counter_name):
        await ctx.reply(f"Counter \"{counter_name}\" exists already.")
        return

    create_counter(ctx.author.id, counter_name)
    if counter_exists(counter_name):
        await ctx.reply(f"Counter \"{counter_name}\" created succesfully.")
    else:
        await ctx.reply(f"Error during creation of counter \"{counter_name}\". Ask Roland to check the logs.")

@bot.command()
async def update_counter(ctx, counter_name: str, amount: int):
    counter_name = counter_name_normalization(counter_name)
    if not counter_exists(counter_name):
        create_counter(ctx.author.id, counter_name)
        if not counter_exists(counter_name):
            await ctx.reply(f"Error during creation of counter \"{counter_name}\". Ask Roland to check the logs.")
            return

    if not is_owner_of_counter(ctx.author.id, counter_name):
        await ctx.reply("Make your own. Dipshit.")
        return

    #TODO: add possibility to ask for permission

    if not update_counter_by_amount(ctx.author.id, counter_name, amount):
        await ctx.reply("Some error. Ask Roland to check the logs.")
        return
        
    current_value = get_current_counter_value(counter_name)
        
    await ctx.reply(f"{counter_name} = {current_value}")


@bot.command()
async def plus(ctx, counter_name: str, amount: int):
    await update_counter(ctx, counter_name, amount)


@bot.command()
async def minus(ctx, counter_name: str, amount: int):
    await update_counter(ctx, counter_name, -amount)
    
    
bot_token = env["DISCORD_BOT_TOKEN"]
log.info("Starting bot")
bot.run(bot_token, log_handler=log_handler)
