import asyncio
import nest_asyncio
import nest_asyncio


def do_nest_async():
    if not hasattr(asyncio, '_nest_patched'):
        nest_asyncio.apply()
    elif not asyncio._nest_patched:
        nest_asyncio.apply()

def do_run_on_event_loop(to_run, err_callback, to_run_loop):
    close_loop = False

    try:
        asyncio.get_running_loop()
        do_nest_async()
    except RuntimeError as r:
        pass

    try:
        to_run_loop = asyncio.get_event_loop()
    except:
        try:
            to_run_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(to_run_loop)
            close_loop = True
        except:
            pass


    try:
        ran = to_run_loop.run_until_complete(to_run)
    except RuntimeError as e:
        if 'This event loop is already running' in str(e):
            do_nest_async()
            try:
                ran = to_run_loop.run_until_complete(to_run)
            except Exception as e:
                return err_callback(str(e))
        else:
            return err_callback(str(e))

    if close_loop:
        to_run_loop.close()
        asyncio.set_event_loop(None)

    return ran
