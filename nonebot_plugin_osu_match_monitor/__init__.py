import asyncio
from typing import Dict, List
import httpx
import logging
from datetime import datetime, timedelta
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from .config import api_key, refresh_interval

logger = logging.getLogger(__name__)

__plugin_meta__ = PluginMetadata(
    name="osu! Match Monitor",
    description="A NoneBot2 plugin used to monitor osu! match activities using match id",
    usage="""
.osu match monitor <房间ID>  开始监控指定房间
.osu match stopmonitor <房间ID>  停止监控指定房间
""",
    type="application",
    homepage="https://github.com/Sevenyine/nonebot-plugin-osu-match-monitor",
)

API_KEY = api_key
REFRESH_INTERVAL = refresh_interval
API_URL_MATCH = "https://osu.ppy.sh/api/get_match"
API_URL_USER = "https://osu.ppy.sh/api/get_user"
API_URL_BEATMAP = "https://osu.ppy.sh/api/get_beatmaps"


monitoring_rooms: Dict[str, Dict] = {}
user_cache: Dict[str, Dict] = {} 
beatmap_cache: Dict[str, Dict] = {}

monitor = on_command("osu match monitor", aliases={"osumonitor"}, priority=5)
stop_monitor = on_command("osu match stop", aliases={"osustopmonitor"}, priority=5)


@monitor.handle()
async def handle_monitor(bot: Bot, event: Event, args: Message = CommandArg()):
    room_id = args.extract_plain_text().strip()
    logger.debug(f"收到监控命令，房间ID：{room_id}")
    if not room_id.isdigit():
        await monitor.finish("请输入有效的房间ID。")
        return

    if room_id in monitoring_rooms:
        await monitor.finish(f"房间 {room_id} 已在监控列表中。")
        return

    match_info = await get_match_info(room_id)
    if match_info and "match" in match_info:
        end_time = match_info["match"].get("end_time")
        if end_time:
            room_info = format_match_info(match_info["match"])
            await monitor.finish(f"房间 {room_id} 已关闭，无法监控。\n房间信息：\n{room_info}")
            logger.info(f"房间 {room_id} 已关闭，无法监控。")
        else:
            await monitor.send(f"开始监控房间 {room_id}：\n{format_match_info(match_info['match'])}")
            # 检查是否有正在进行的比赛
            games = match_info.get('games', [])
            ongoing_game = None
            for game in games:
                if game.get('start_time') and not game.get('end_time'):
                    ongoing_game = game
                    break

            if ongoing_game:
                message = f"当前正在进行的比赛（Game ID: {ongoing_game['game_id']}）：\n"
                message += await format_game_info(ongoing_game)
                await monitor.send(message)
                beatmap_id = ongoing_game.get("beatmap_id", "")
                if beatmap_id:
                    cover_image = await get_beatmap_cover(beatmap_id)
                    if cover_image:
                        await monitor.send(MessageSegment.image(cover_image))

            monitoring_rooms[room_id] = match_info
            logger.info(f"开始监控房间 {room_id}")
            asyncio.create_task(monitor_room(bot, event, room_id))
            return
    else:
        await monitor.finish("无法获取房间信息，请检查房间ID是否正确。")
        logger.error(f"获取房间 {room_id} 信息失败")

@stop_monitor.handle()
async def handle_stop_monitor(args: Message = CommandArg()):
    room_id = args.extract_plain_text().strip()
    logger.debug(f"收到停止监控命令，房间ID：{room_id}")
    if room_id in monitoring_rooms:
        monitoring_rooms.pop(room_id)
        await stop_monitor.send(f"已停止监控房间 {room_id}。")
        logger.info(f"已停止监控房间 {room_id}")
    else:
        await stop_monitor.send(f"未找到正在监控的房间 {room_id}。")
        logger.warning(f"试图停止未监控的房间 {room_id}")

async def monitor_room(bot: Bot, event: Event, room_id: str):
    logger.debug(f"进入房间 {room_id} 的监控循环")
    previous_match_info = None
    while room_id in monitoring_rooms:
        try:
            new_match_info = await get_match_info(room_id)
            if new_match_info and "games" in new_match_info:
                if previous_match_info is None:
                    previous_match_info = new_match_info
                    monitoring_rooms[room_id] = new_match_info
                else:
                    if new_match_info["match"] != previous_match_info.get("match"):
                        await bot.send(event, f"房间 {room_id} 信息更新：\n{format_match_info(new_match_info['match'])}")
                        logger.info(f"房间 {room_id} 信息更新")

                    previous_games = previous_match_info.get("games", [])
                    new_games = new_match_info.get("games", [])
                    previous_games_dict = {game["game_id"]: game for game in previous_games}
                    new_games_dict = {game["game_id"]: game for game in new_games}

                    for game_id, game in new_games_dict.items():
                        prev_game = previous_games_dict.get(game_id)
                        if not prev_game:
                            # 比赛开始
                            message = f"房间 {room_id} 的新比赛（Game ID: {game_id}）已开始！\n"
                            message += await format_game_info(game)
                            await bot.send(event, message)
                            # 发送封面图片
                            beatmap_id = game.get("beatmap_id", "")
                            if beatmap_id:
                                cover_image = await get_beatmap_cover(beatmap_id)
                                if cover_image:
                                    await bot.send(event, MessageSegment.image(cover_image))
                            logger.info(f"房间 {room_id} 的新比赛（Game ID: {game_id}）已开始")
                        elif game != prev_game:
                            if game["end_time"] and not prev_game.get("end_time"):
                                # 输出成绩
                                message = f"房间 {room_id} 的比赛（Game ID: {game_id}）已结束，比分如下：\n"
                                message += await format_scores(game['scores'], game.get("play_mode", "0"))
                                await bot.send(event, message)
                                logger.info(f"房间 {room_id} 的比赛（Game ID: {game_id}）已结束")
                                monitoring_rooms.pop(room_id, None)
                                return
                            else:
                                message = f"房间 {room_id} 的比赛（Game ID: {game_id}）有新的更新。\n"
                                message += await format_game_info(game)
                                await bot.send(event, message)
                                logger.info(f"房间 {room_id} 的比赛（Game ID: {game_id}）有新的更新")
                    previous_match_info = new_match_info
                    monitoring_rooms[room_id] = new_match_info
            else:
                await bot.send(event, f"无法获取房间 {room_id} 的信息，停止监控。")
                monitoring_rooms.pop(room_id, None)
                logger.error(f"无法获取房间 {room_id} 的信息，停止监控")
                break
        except Exception as e:
            logger.exception(f"监控房间 {room_id} 时发生异常：{e}")
        await asyncio.sleep(REFRESH_INTERVAL)

async def get_match_info(room_id: str) -> Dict:
    params = {
        "k": API_KEY,
        "mp": room_id
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(API_URL_MATCH, params=params)
            logger.debug(f"请求房间 {room_id} 的比赛信息，状态码：{response.status_code}")
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"房间 {room_id} 的比赛信息：{data}")
                return data
            else:
                logger.error(f"请求房间 {room_id} 信息失败，状态码：{response.status_code}")
    except Exception as e:
        logger.exception(f"获取比赛信息时出错：{e}")
    return {}

async def get_user_info(user_id: str) -> Dict:
    if user_id in user_cache:
        return user_cache[user_id]
    params = {
        "k": API_KEY,
        "u": user_id,
        "type": "id"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(API_URL_USER, params=params)
            if response.status_code == 200:
                data = response.json()
                if data:
                    user_info = data[0]
                    user_cache[user_id] = user_info
                    return user_info
            else:
                logger.error(f"请求用户 {user_id} 信息失败，状态码：{response.status_code}")
    except Exception as e:
        logger.exception(f"获取用户信息时出错：{e}")
    return {}

async def get_beatmap_info(beatmap_id: str) -> Dict:
    if beatmap_id in beatmap_cache:
        return beatmap_cache[beatmap_id]
    params = {
        "k": API_KEY,
        "b": beatmap_id,
        "limit": 1
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(API_URL_BEATMAP, params=params)
            if response.status_code == 200:
                data = response.json()
                if data:
                    beatmap_info = data[0]
                    beatmap_cache[beatmap_id] = beatmap_info
                    return beatmap_info
            else:
                logger.error(f"请求谱面 {beatmap_id} 信息失败，状态码：{response.status_code}")
    except Exception as e:
        logger.exception(f"获取谱面信息时出错：{e}")
    return {}

async def get_beatmap_cover(beatmap_id: str) -> str:
    beatmap_info = await get_beatmap_info(beatmap_id)
    if beatmap_info:
        beatmapset_id = beatmap_info.get("beatmapset_id", "")
        if beatmapset_id:
            cover_url = f"https://assets.ppy.sh/beatmaps/{beatmapset_id}/covers/cover.jpg"
            return cover_url
    return ""

def format_match_info(match: Dict) -> str:
    match_id = match.get("match_id", "未知")
    name = match.get("name", "未知")
    start_time = convert_to_utc8(match.get("start_time", "未知"))
    end_time = "进行中" if match.get("end_time") is None else convert_to_utc8(match.get("end_time"))
    return f"房间ID：{match_id}\n房间名：{name}\n开始时间：{start_time}\n结束时间：{end_time}"

async def format_game_info(game: Dict) -> str:
    start_time = convert_to_utc8(game.get("start_time", "未知"))
    end_time = "进行中" if game.get("end_time") is None else convert_to_utc8(game.get("end_time"))
    beatmap_id = game.get("beatmap_id", "未知")
    beatmap_info = await get_beatmap_info(beatmap_id)
    beatmap_title = f"{beatmap_info.get('artist', '')} - {beatmap_info.get('title', '')} [{beatmap_info.get('version', '')}]" if beatmap_info else f"未知谱面（ID: {beatmap_id}）"
    play_mode = get_play_mode(game.get("play_mode", "未知"))
    scoring_type = get_scoring_type(game.get("scoring_type", "未知"))
    team_type = get_team_type(game.get("team_type", "未知"))
    mods = get_mods(game.get("mods", "0"))
    return (f"开始时间：{start_time}\n"
            f"结束时间：{end_time}\n"
            f"谱面：{beatmap_title}\n"
            f"游戏模式：{play_mode}\n"
            f"胜利条件：{scoring_type}\n"
            f"队伍类型：{team_type}\n"
            f"Global Mods：{mods}\n")

async def format_scores(scores: List[Dict], play_mode_code: str) -> str:
    score_messages = []
    for score in scores:
        slot = score.get("slot", "未知")
        team = get_team(score.get("team", "0"))
        user_id = score.get("user_id", "未知")
        user_info = await get_user_info(user_id)
        username = user_info.get("username", "未知用户")
        country_code = user_info.get("country", "")
        user_display = f"[@{country_code}] {username} ({user_id})"

        user_score = score.get("score", "0")
        maxcombo = score.get("maxcombo", "0")
        countmiss = score.get("countmiss", "0")
        count50 = score.get("count50", "0")
        count100 = score.get("count100", "0")
        countkatu = score.get("countkatu", "0")  # 200 或 osu!catch 的 miss droplets
        count300 = score.get("count300", "0")
        countgeki = score.get("countgeki", "0")  # 300+ 或 osu!catch 的 caught droplets
        perfect = score.get("perfect", "0")
        pass_status = score.get("pass", "0")
        enabled_mods = get_mods(score.get("enabled_mods", "0"))
        play_mode = play_mode_code
        score_v2 = "ScoreV2" in enabled_mods

        accuracy = calculate_accuracy(
            count50, count100, count300, countmiss, countkatu, countgeki, play_mode, score_v2
        )
        combo_display = f"{maxcombo}" + (" (FC)" if perfect == "1" else "")
        pass_message = "PASS" if pass_status == "1" else "FAIL"

        score_messages.append(
            f"玩家：{user_display}\n"
            f"分数：{user_score}  Acc：{accuracy}%  连击：{combo_display}\n"
            f"300+：{countgeki}  300：{count300}  200：{countkatu}\n"
            f"100：{count100}  50：{count50}  MISS：{countmiss}\n"
            f"{pass_message}  Mods：{enabled_mods}\n"
        )
    return "\n".join(score_messages)

def get_play_mode(mode_code: str) -> str:
    modes = {
        "0": "osu!",
        "1": "osu!taiko",
        "2": "osu!catch",
        "3": "osu!mania"
    }
    return modes.get(mode_code, "未知")

def get_scoring_type(type_code: str) -> str:
    types = {
        "0": "Score",
        "1": "Accuracy",
        "2": "Combo",
        "3": "Score v2"
    }
    return types.get(type_code, "未知")

def get_team_type(type_code: str) -> str:
    types = {
        "0": "Head to Head",
        "1": "Tag Co-op",
        "2": "Team Vs",
        "3": "Tag Team Vs"
    }
    return types.get(type_code, "未知")

def get_mods(mods_code: str) -> str:
    mods_int = int(mods_code)
    mod_list = []
    mods_mapping = {
        1 << 0: "NoFail",
        1 << 1: "Easy",
        1 << 2: "TouchDevice",
        1 << 3: "Hidden",
        1 << 4: "HardRock",
        1 << 5: "SuddenDeath",
        1 << 6: "DoubleTime",
        1 << 7: "Relax",
        1 << 8: "HalfTime",
        1 << 9: "Nightcore",
        1 << 10: "Flashlight",
        1 << 11: "Autoplay",
        1 << 12: "SpunOut",
        1 << 13: "Autopilot",
        1 << 14: "Perfect",
        1 << 15: "Key4",
        1 << 16: "Key5",
        1 << 17: "Key6",
        1 << 18: "Key7",
        1 << 19: "Key8",
        1 << 20: "FadeIn",
        1 << 21: "Random",
        1 << 22: "Cinema",
        1 << 23: "Target",
        1 << 24: "Key9",
        1 << 25: "KeyCoop",
        1 << 26: "Key1",
        1 << 27: "Key3",
        1 << 28: "Key2",
        1 << 29: "ScoreV2",
        1 << 30: "Mirror",
    }
    # Nightcore = DoubleTime + Nightcore
    if mods_int & (1 << 9):
        mods_int &= ~(1 << 6)
    # Perfect = SuddenDeath + Perfect
    if mods_int & (1 << 14):
        mods_int &= ~(1 << 5)

    for mod_value, mod_name in sorted(mods_mapping.items()):
        if mods_int & mod_value:
            mod_list.append(mod_name)
    return "+".join(mod_list) if mod_list else "None"

def get_team(team_code: str) -> str:
    teams = {
        "0": "None",
        "1": "Blue",
        "2": "Red"
    }
    return teams.get(team_code, "未知")

def convert_to_utc8(utc_time_str: str) -> str:
    try:
        utc_time = datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')
        utc8_time = utc_time + timedelta(hours=8)
        return utc8_time.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logger.error(f"时间转换失败：{e}")
        return utc_time_str

def calculate_accuracy(count50, count100, count300, countmiss, countkatu, countgeki, mode, score_v2=False):
    mode = int(mode)
    count50 = int(count50)
    count100 = int(count100)
    count300 = int(count300)
    countmiss = int(countmiss)
    countkatu = int(countkatu)
    countgeki = int(countgeki)
    if mode == 0:  # osu!
        total_hits = count50 + count100 + count300 + countmiss
        if total_hits == 0:
            return "0.00"
        accuracy = (50 * count50 + 100 * count100 + 300 * count300) / (300 * total_hits) * 100
    elif mode == 1:  # osu!taiko
        total_hits = count300 + count100 + countmiss
        if total_hits == 0:
            return "0.00"
        accuracy = (count300 + 0.5 * count100) / total_hits * 100
    elif mode == 2:  # osu!catch
        total_caught = count300 + count100 + count50
        total_objects = count300 + count100 + count50 + countmiss + countkatu
        if total_objects == 0:
            return "0.00"
        accuracy = total_caught / total_objects * 100
    elif mode == 3:  # osu!mania
        total_notes = countgeki + count300 + countkatu + count100 + count50 + countmiss
        if total_notes == 0:
            return "0.00"
        if score_v2:
            accuracy = (
                305 * countgeki + 300 * count300 + 200 * countkatu + 100 * count100 + 50 * count50
            ) / (305 * total_notes) * 100
        else:
            accuracy = (
                300 * (countgeki + count300) + 200 * countkatu + 100 * count100 + 50 * count50
            ) / (300 * total_notes) * 100
    else:
        return "0.00"
    return f"{accuracy:.2f}"