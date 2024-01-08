from typing import List
import logging
from os import environ as env

import discord
from discord.ext import commands, tasks
from datetime import time
from src.db import get_conn, run_sql
from zoneinfo import ZoneInfo

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


def is_public(counter_name: str) -> bool:
    query = "SELECT is_public FROM counters WHERE label = %s"
    return run_sql(conn.cursor(), query, (counter_name,))[0][0]


def update_counter_by_amount(author: int, counter_name: str, amount: int) -> bool:
    counter_id = get_counter_id(counter_name)
    query = "INSERT INTO counter_updates (author, \"counter_id\", amount) VALUES (%s, %s, %s);"
    try:
        run_sql(conn.cursor(), query, (author, counter_id, amount))
    except:
        return False

    return True


def create_counter(user_owner: int, counter_name: str):
    query = "INSERT INTO counters (author, label) VALUES (%s, %s);"
    run_sql(conn.cursor(), query, (user_owner, counter_name))


def user_owned_counters(user_owner: int) -> List[str]:
    query = "SELECT label from counters WHERE author = %s"
    ret = run_sql(conn.cursor(), query, (user_owner,))
    return [counter[0] for counter in ret]


def daily_counters() -> List[str]:
    query = "SELECT label, daily from counters WHERE daily != 0"
    return run_sql(conn.cursor(), query, (0,))


def public_counters() -> List[str]:
    query = "SELECT label from counters WHERE is_public = TRUE"
    ret = run_sql(conn.cursor(), query)
    return [counter[0] for counter in ret]

@bot.command()
async def citace(ctx):
    public = public_counters()
    counters = set(user_owned_counters(ctx.author.id) + public)
    message = "\n".join(f"{counter} = {get_current_counter_value(counter)}{' (public)' if counter in public else ''}" for counter in counters)
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
async def opravneni(ctx, counter_name: str):
    counter_name = counter_name_normalization(counter_name)
    if counter_exists(counter_name):
        counter_id = get_counter_id(counter_name)
        query = "SELECT is_public FROM counters WHERE id = %s"
        permissions = run_sql(conn.cursor(), query, (counter_id,))[0][0]
        print(permissions)
        await ctx.reply(f"Counter \"{counter_name}\" is {'public' if permissions else 'private'}")
        return

    await ctx.reply(f"Counter \"{counter_name}\" doesn't exist.")


@bot.command()
async def counter_create(ctx, counter_name: str):
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

    if not (is_owner_of_counter(ctx.author.id, counter_name) or is_public(counter_name)):
        await ctx.reply("Make your own. Dipshit.")
        return

    if not update_counter_by_amount(ctx.author.id, counter_name, amount):
        await ctx.reply("Some error. Ask Roland to check the logs.")
        return

    current_value = get_current_counter_value(counter_name)

    await ctx.reply(f"{counter_name} = {current_value}")


@bot.command()
async def zverejnit(ctx, counter_name: str, is_public: bool):
    counter_name = counter_name_normalization(counter_name)
    if not counter_exists(counter_name):
        await ctx.reply(f"Counter \"{counter_name}\" does not exist.")
        return

    if not is_owner_of_counter(ctx.author.id, counter_name):
        await ctx.reply("Nice try dumbass.")
        return

    counter_id = get_counter_id(counter_name)
    query = f"UPDATE counters SET is_public={'TRUE' if is_public else 'FALSE'} WHERE id = %s;"
    run_sql(conn.cursor(), query, (counter_id,))

    await ctx.reply(f"Counter \"{counter_name}\" is now {'public' if is_public else 'private'}")


@bot.command()
async def nastav(ctx, counter_name: str, amount: int):
    if counter_exists(counter_name):
        update_counter_by_amount(bot.user.id, counter_name, -get_current_counter_value(counter_name_normalization(counter_name)))
    await update_counter(ctx, counter_name, amount)


@bot.command()
async def plus(ctx, counter_name: str, amount: int):
    await update_counter(ctx, counter_name, amount)


@bot.command()
async def minus(ctx, counter_name: str, amount: int):
    await update_counter(ctx, counter_name, -amount)


@bot.command()
async def denne(ctx, counter_name: str, amount: int):
    if not (is_owner_of_counter(ctx.author.id, counter_name) or counter_name in public_counters()):
        await ctx.reply("Make your own. Dipshit.")
        return

    counter_id = get_counter_id(counter_name)
    query = "UPDATE counters SET daily=%s WHERE id = %s;"
    try:
        run_sql(conn.cursor(), query, (amount, counter_id))
    except:
        await ctx.reply("Some error. Ask Roland to check the logs.")
        return False

    await ctx.reply(f"Daily updates set to {amount}")
    return True


@bot.command()
async def pomoc(ctx):
    help_message="""
```
/plus "jmeno" 1         -- Přičte hodnotu k čítači
/minus "jmeno" 1        -- Odečte hodnotu z čítače
/nastav "jmeno" 1       -- Nastaví hodnotu čítače
/citac "jmeno"          -- Vypsat aktuální hodnotu čítače
/citace                 -- Vypsat všechny mnou dostupné čítače
/opravneni "jmeno"      -- Vypsat veřejnost čítače
/zverejnit "jmeno" True -- Nastavit veřejnost čítače
/denne "jmeno" 1        -- Denně aktaulizuje hodnotu čítače přičtením hodnoty
```
"""
    await ctx.reply(help_message)


@tasks.loop(time=time(hour=0, tzinfo=ZoneInfo("Europe/Prague")))
async def daily_increment():
    counters = daily_counters()
    print(counters)
    for counter in counters:
        update_counter_by_amount(bot.user.id, counter[0], int(counter[1]))


@bot.event
async def on_ready():
    daily_increment.start()


bot_token = env["DISCORD_BOT_TOKEN"]
log.info("Starting bot")
bot.run(bot_token, log_handler=log_handler)
