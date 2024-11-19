import multiprocessing
import users_bot
import admin_bot

def run_users_bot():
    try:
        users_bot.main()
    except Exception as e:
        print(f"Users bot encountered an error:{e}")

def run_admin_bot():
    try:
        admin_bot.main()
    except Exception as e:
        print(f"Admin bot encountered an error:{e}")
    except Exception as e:
        print(f"Barcode client bot error : {e} ")
if __name__ == '__main__':
    admin_process = multiprocessing.Process(target=run_admin_bot)
    users_process = multiprocessing.Process(target=run_users_bot)
    users_process.start()
    admin_process.start()
