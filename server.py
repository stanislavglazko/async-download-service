import aiohttp
from aiohttp import web
import aiofiles
import argparse
import asyncio
import functools
import logging
import os
from environs import Env


env = Env()
env.read_env()

ZIP_ARGS = ['zip', '-r', '-', '.']
DEFAULT_CHUNK_SIZE = 500000
DEBUG, INFO, WARNING, ERROR, CRITICAL = \
    'debug', 'info', 'error', 'warning', 'critical'

DEFAULT_DIR_WITH_PHOTOS = env.str('DEFAULT_DIR_WITH_PHOTOS', 'test_photos')
DEFAULT_LOGGING_LEVEL = env.str('DEFAULT_LOGGING_LEVEL', INFO)
DEFAULT_RESPONSE_DELAY = env.int('DEFAULT_RESPONSE_DELAY', 0)


def get_parser_args():
    parser = argparse.ArgumentParser(description='Download photos archive')
    parser.add_argument('-rd', '--response_delay', type=int, default=DEFAULT_RESPONSE_DELAY)
    parser.add_argument('-ll', '--logging_level', type=str, default=DEFAULT_LOGGING_LEVEL)
    parser.add_argument('-f', '--folder_with_photos', type=str, default=DEFAULT_DIR_WITH_PHOTOS)

    return parser.parse_args()


def set_logging_level(level_logging):
    logging_levels_mapping = {
        DEBUG: logging.DEBUG,
        WARNING: logging.WARNING,
        ERROR: logging.ERROR,
        CRITICAL: logging.CRITICAL,
        INFO: logging.INFO,
    }

    return logging.basicConfig(level = logging_levels_mapping[level_logging])


async def download_archive(request, response_delay, folder_with_photos):
    archive_hash = request.match_info.get('archive_hash')
    path_to_photos = os.path.join(folder_with_photos, archive_hash)

    if not os.path.exists(path_to_photos):
        raise aiohttp.web.HTTPNotFound(text='The archive was deleted')

    response = web.StreamResponse()
    response.headers['Content-Disposition'] = f'attachment; filename="{archive_hash}.zip'

    await response.prepare(request)

    process = await asyncio.create_subprocess_exec(
            *ZIP_ARGS,
            cwd=path_to_photos,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    try:
        while True:
            archive = await process.stdout.read(n=DEFAULT_CHUNK_SIZE)
            logging.info('Sending archive chunk ...')
            await response.write(archive)
            if process.stdout.at_eof():
                return response
            await asyncio.sleep(response_delay)
    except asyncio.CancelledError:
        logging.error('Download was interrupted')
        process.kill()
        raise
    finally:
        response.force_close()


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    parser_args = get_parser_args()
    set_logging_level(parser_args.logging_level)
    app = web.Application()

    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', functools.partial(
            download_archive,
            response_delay=parser_args.response_delay,
            folder_with_photos=parser_args.folder_with_photos,
            )
        ),
    ])
    
    web.run_app(app)
