from termcolor import colored

def green(data):
    print(colored(data,'green'))

def red(data):
    print(colored(data,'red'))

def light_red(data):
    print(colored(data,'light_red'))

def yellow(data):
    print(colored(data,'yellow'))

def yellow_input(data):
    data = input(colored(data,'yellow'))
    return data

def cyan(data):
    print(colored(data,'magenta'))

def magenta(data):
    print(colored(data,'magenta'))