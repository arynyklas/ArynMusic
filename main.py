from pyrogram import Client, filters, types

from pytgcalls import GroupCallFactory
from pytgcalls.implementation.group_call_file import GroupCallFile

from yandex_music import Track
from uuid import uuid4
from ffmpeg import input as ffmpeg_url
from os import remove

from music import Music
from utils import get_config, save_config, download_file
from basic_data import texts

from typing import List


config_filename: str = "config.json"
config: dict = get_config(config_filename)


client: Client = Client(
    session_name = str(config["api_id"]),
    api_id = config["api_id"],
    api_hash = config["api_hash"]
)


group_call: GroupCallFile = GroupCallFactory(
    client = client
).get_file_group_call()


music: Music = Music(
    token = config["yandex"]["token"],
    username = config["yandex"]["username"],
    password = config["yandex"]["password"]
)


config["yandex"]["token"] = music._client.token

save_config(
    filename = config_filename,
    data = config
)


input_filename: str = "input.raw"


main_filter: filters.Filter = filters.text & filters.chat(
    chats = [config["listener_chat_id"]]
) & filters.user(
    users = config["owners"]
) & ~filters.edited


def cmd_filter(*commands: str) -> filters.Filter:
    return filters.command(
        commands = [*commands],
        prefixes = ["!", "/", "."]
    )


async def play_next() -> None:
    if music.on_replay:
        return

    track: Track = music.start_radio() if music.is_playing_track else music.play_next()

    music.is_playing_track = False

    audio_original: str = "{uuid}.mp3".format(
        uuid = uuid4()
    )

    download_url: str = music.track_download_url(
        track = track
    )

    await download_file(
        url = download_url,
        filename = audio_original
    )

    ffmpeg_url(audio_original).output(
        input_filename,
        format = "s16le",
        acodec = "pcm_s16le",
        ac = 2,
        ar = "48k"
    ).overwrite_output().run()

    remove(audio_original)

    group_call.input_filename = input_filename

    if not group_call.is_connected:
        await group_call.start(
            group = config["voice_chat_id"]
        )


@group_call.on_playout_ended
async def on_playout_ended(_: GroupCallFile, *__: str):
    group_call.stop_playout()
    await play_next()


@client.on_message(main_filter & cmd_filter("play", "p"))
async def play_command_handler(_: Client, message: types.Message) -> None:
    args: List[str] = message.text.split(" ", maxsplit=1)

    if len(args) < 2:
        return await message.delete()

    tracks: List[Track] = music.search_tracks(
        query = args[1]
    )

    if len(tracks) < 1:
        return await message.delete()

    track: Track = tracks[0]

    music.on_replay = False
    music.is_playing_track = True

    del tracks, args

    message_: types.Message = await message.reply_text(
        text = texts["downloading"]
    )

    audio_original: str = "{uuid}.mp3".format(
        uuid = uuid4()
    )

    download_url: str = music.track_download_url(
        track = track
    )

    await download_file(
        url = download_url,
        filename = audio_original
    )

    await message_.edit_text(
        text = texts["converting"]
    )

    ffmpeg_url(audio_original).output(
        input_filename,
        format = "s16le",
        acodec = "pcm_s16le",
        ac = 2,
        ar = "48k"
    ).overwrite_output().run()

    remove(audio_original)

    await message_.edit_text(
        text = texts["playing"].format(
            artists = ", ".join(track.artists_name()),
            title = track.title
        )
    )

    group_call.input_filename = input_filename

    if not group_call.is_connected:
        await group_call.start(
            group = config["voice_chat_id"]
        )


@client.on_message(main_filter & cmd_filter("volume", "v"))
async def volume_command_handler(_: Client, message: types.Message):
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text(
            text = texts["volume_ng"]
        )

    volume: int = int(message.command[1])

    await group_call.set_my_volume(volume)

    await message.reply_text(
        text = texts["volume_changed"].format(
            volume = volume
        )
    )


@client.on_message(main_filter & cmd_filter("join", "j"))
async def join_command_handler(_: Client, message: types.Message):
    await group_call.start(
        group = config["voice_chat_id"]
    )

    await message.reply_text(
        text = texts["joined"]
    )


@client.on_message(main_filter & cmd_filter("leave", "l"))
async def leave_command_handler(_: Client, message: types.Message):
    await group_call.leave_current_group_call()

    await message.reply_text(
        text = texts["leaved"]
    )


@client.on_message(main_filter & cmd_filter("rejoin", "rj"))
async def rejoin_command_handler(_: Client, message: types.Message):
    await group_call.reconnect()

    await message.reply_text(
        text = texts["rejoined"]
    )


@client.on_message(main_filter & cmd_filter("replay", "rp"))
async def restart_command_handler(_: Client, message: types.Message):
    group_call.restart_playout()

    music.on_replay = True

    await message.reply_text(
        text = texts["on_replay"]
    )


@client.on_message(main_filter & cmd_filter("stop"))
async def stop_command_handler(_: Client, message: types.Message):
    group_call.stop_playout()

    await message.reply_text(
        text = texts["stopped"]
    )


@client.on_message(main_filter & cmd_filter("skip", "s", "next", "x"))
async def skip_command_handler(_: Client, message: types.Message):
    group_call.stop_playout()

    await message.reply_text(
        text = texts["skipped"]
    )

    await play_next()


@client.on_message(main_filter & cmd_filter("pause", "p"))
async def pause_command_handler(_: Client, message: types.Message):
    group_call.pause_playout()

    await message.reply_text(
        text = texts["paused"]
    )


@client.on_message(main_filter & cmd_filter("resume", "rs"))
async def resume_command_handler(_: Client, message: types.Message):
    group_call.resume_playout()

    await message.reply_text(
        text = texts["resumed"]
    )


if __name__ == "__main__":
    client.run()
