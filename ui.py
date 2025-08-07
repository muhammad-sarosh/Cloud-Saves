from rich.prompt import Prompt
from rich import print

# Takes integer input until valid
def int_range_input(input_message, min, max):
    while True:
        choice = Prompt.ask(input_message).strip()
        try: 
            choice = int(choice)
            if not (min <= choice <= max):
                print('Input out of range')
            else:
                return choice
        except ValueError:
            print('Input must be a valid number\n')

def str_input(input_message):
    data = ''
    while data == '':
        data = Prompt.ask(input_message).strip()
        if data == '':
            print('Input cannot be empty')
    return data


def get_supabase_info(choice):
    if choice == 'url':
        input_message = 'Enter your supabase data api url'
    elif choice == 'api key':
        input_message = 'Enter your supabase service_role api key'
    elif choice == 'bucket name':
        input_message = 'Enter your supabase bucket name'
    elif choice == 'table name':
        input_message = 'Enter your supabase database table name'
    data = str_input(input_message)
    return data