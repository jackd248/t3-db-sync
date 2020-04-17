#!/usr/bin/python

import argparse, sys, os, time, calendar, shutil, argparse
from subprocess import check_output
import getpass
import json

#
# GLOBALS
#
config = {}
remote_ssh_password = None
remote_database_dump_file_name = None
ssh_client = None
keep_dump_option = False

#
# DEFAULTS
#
default_local_host_file_path = 'host.json'
default_local_sync_path = os.path.abspath(os.getcwd()) + '/.sync/'
default_ignore_database_tables = [
    'sys_domain',
    'cf_cache_hash',
    'cf_cache_hash_tags',
    'cf_cache_news_category',
    'cf_cache_news_category_tags',
    'cf_cache_pages',
    'cf_cache_pagesection',
    'cf_cache_pagesection_tags',
    'cf_cache_pages_tags',
    'cf_cache_rootline',
    'cf_cache_rootline_tags',
    'cf_extbase_datamapfactory_datamap',
    'cf_extbase_datamapfactory_datamap_tags',
    'cf_extbase_object',
    'cf_extbase_object_tags',
    'cf_extbase_reflection',
    'cf_extbase_reflection_tags',
]

def main():
    global config
    global default_local_host_file_path
    global default_local_sync_path
    global default_local_sync_path
    global keep_dump_option

    print(bcolors.BLACK + '###############################' + bcolors.ENDC)
    print(bcolors.BLACK + '#' + bcolors.ENDC + '     TYPO3 Database Sync     ' + bcolors.BLACK + '#' + bcolors.ENDC)
    print(bcolors.BLACK + '###############################' + bcolors.ENDC)

    parser = argparse.ArgumentParser()
    parser.add_argument('-f','--file', help='Path to host file', required=False)
    parser.add_argument('-kd','--keepdump', help='Skipping local import of the database dump and saving the available dump file in the given directory', required=False)
    args = parser.parse_args()

    if not args.file is None:
        default_local_host_file_path = args.file

    if not args.keepdump is None:
        default_local_sync_path = args.keepdump
        if default_local_sync_path[-1] != '/':
            default_local_sync_path += '/'
        keep_dump_option = True
        _print(subject.INFO, '"Keep dump" option chosen', True)

    check_configuration()
    create_remote_database_dump()
    get_remote_database_dump()
    import_database_dump()
    clean_up()

    ssh_client.close()
    _print(subject.INFO, 'Successfully synchronized databases', True)

#
# CHECK CONFIGURATION
#
def check_configuration():
    global ssh_client
    get_host_configuration()
    load_pip_modules()
    get_remote_password()
    check_local_configuration()

    ssh_client = get_ssh_client()
    check_remote_configuration()

def get_host_configuration():
    if os.path.isfile(default_local_host_file_path):
        with open(default_local_host_file_path, 'r') as read_file:
            config['host'] = json.load(read_file)
            _print(subject.LOCAL, 'Loading host configuration', True)

            if 'ignore_table' in config['host']:
                config['ignore_table'] = config['host']['ignore_table']
            else:
                config['ignore_table'] = default_ignore_database_tables
    else:
        sys.exit(_print(subject.ERROR, 'Local host configuration not found', False))

def load_pip_modules():
    import importlib
    import subprocess

    try:
        import pip
    except ImportError:
        sys.exit(_print(subject.ERROR, 'Pip is not installed', False))

    _print(subject.LOCAL, 'Checking pip modules', True)
    package = 'paramiko'
    try:
        globals()[package] = importlib.import_module(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        sys.exit(_print(subject.INFO, 'First install of additional pip modules completed. Please re-run the script.', False))

def get_remote_password():
    global remote_ssh_password
    _password = getpass.getpass(_print(subject.INFO, 'SSH password for user "' + config['host']['remote']['user'] + '" (' + config['host']['remote']['host'] + '): ', False))

    while _password.strip() is '':
            _print(subject.INFO, 'Password is empty. Please enter a valid password.', True)
            _password = getpass.getpass(_print(subject.INFO, 'SSH password for user "' + config['host']['remote']['user'] + '" (' + config['host']['remote']['host'] + '): ', False))

    remote_ssh_password = _password

def check_local_configuration():
    if os.path.isfile(config['host']['local']['path']) == False:
        sys.exit(_print(subject.ERROR, 'Local database configuration not found', False))

    config['db'] = {}
    #
    # https://stackoverflow.com/questions/7290357/how-to-read-a-php-array-from-php-file-in-python
    #
    _local_db_config = check_output(['php', '-r', 'echo json_encode(include "' + config['host']['local']['path'] + '");'])
    _local_db_config = json.loads(_local_db_config)['DB']['Connections']['Default']
    _print(subject.LOCAL, 'Checking database configuration', True)
    config['db']['local'] = _local_db_config

def check_remote_configuration():
    stdout = run_ssh_command('php -r "echo json_encode(include \'' + config['host']['remote']['path'] + '\');"')
    _remote_db_config = stdout.readlines()[0]
    _remote_db_config = json.loads(_remote_db_config)['DB']['Connections']['Default']
    config['db']['remote'] = _remote_db_config
    _print(subject.REMOTE, 'Checking database configuration', True)

#
# CREATE REMOTE DATABASE DUMP
#
def create_remote_database_dump():
    generate_database_dump_filename()

    _print(subject.REMOTE, 'Creating database dump', True)
    run_ssh_command('mysqldump ' + generate_mysql_credentials('remote') + ' ' + config['db']['remote']['dbname'] + ' --ignore-table=' + generate_ignore_database_tables() + ' > ~/' + remote_database_dump_file_name)
    prepare_remote_database_dump()

def prepare_remote_database_dump():
    _print(subject.REMOTE, 'Compress database dump', True)
    run_ssh_command('tar cfvz ~/' + remote_database_dump_file_name + '.tar.gz ' + remote_database_dump_file_name)

def generate_database_dump_filename():
    # _project_typo3_db_dump_1586780116.sql
    global remote_database_dump_file_name
    _timestamp = calendar.timegm(time.gmtime())
    remote_database_dump_file_name =  '_' + config['host']['name'] + '_typo3_db_dump_' + str(_timestamp) + '.sql'

def generate_ignore_database_tables():
    _ignore_tables = []
    for table in config['ignore_table']:
        _ignore_tables.append(config['db']['remote']['dbname'] + '.' + table)
    return ','.join(_ignore_tables)

def generate_mysql_credentials(_target):
    _credentials = '-u\'' + config['db'][_target]['user'] + '\' -p\'' + config['db'][_target]['password'] + '\''
    if 'host' in config['db'][_target]:
        _credentials += ' -h\'' + config['db'][_target]['host'] + '\''
    if 'port' in config['db'][_target]:
        _credentials += ' -P\'' + str(config['db'][_target]['port']) + '\''
    return _credentials

#
# GET REMOTE DATABASE DUMP
#
def get_remote_database_dump():
    create_temporary_data_dir()

    sftp = ssh_client.open_sftp()
    _print(subject.REMOTE, 'Downloading database dump', True)
    #
    # ToDo: Download speed problems
    # https://github.com/paramiko/paramiko/issues/60
    #
    sftp.get('/home/' + config['host']['remote']['user'] + '/' + remote_database_dump_file_name + '.tar.gz', default_local_sync_path + remote_database_dump_file_name + '.tar.gz', download_status)
    sftp.close()
    print('')

def create_temporary_data_dir():
    if not os.path.exists(default_local_sync_path):
        os.mkdir(default_local_sync_path)

#
# IMPORT DATABASE DUMP
#
def import_database_dump():
    prepare_local_database_dump()
    check_local_database_dump()

    if not keep_dump_option:
        _print(subject.LOCAL, 'Importing database dump', True)
        os.system('mysql ' + generate_mysql_credentials('local') + ' ' + config['db']['local']['dbname'] + ' < ' + default_local_sync_path + remote_database_dump_file_name)

def prepare_local_database_dump():
    _print(subject.LOCAL, 'Extract database dump', True)
    os.system('tar xzf ' + default_local_sync_path + remote_database_dump_file_name + '.tar.gz')
    os.system('mv ' + os.path.abspath(os.getcwd()) + '/' + remote_database_dump_file_name + ' ' + default_local_sync_path + remote_database_dump_file_name)

def check_local_database_dump():
    with open(default_local_sync_path + remote_database_dump_file_name) as f:
        lines = f.readlines()
        if "-- Dump completed on" not in lines[-1]:
            sys.exit(_print(subject.ERROR, 'Dump was not fully transferred', False))

#
# CLEAN UP
#
def clean_up():
    remove_remote_database_dump()
    if not keep_dump_option:
        remove_temporary_data_dir()
    else:
        _print(subject.INFO, 'Dump file is saved to: ' + default_local_sync_path + remote_database_dump_file_name, True)

def remove_remote_database_dump():

    _print(subject.REMOTE, 'Cleaning up', True)
    sftp = ssh_client.open_sftp()
    sftp.remove('/home/' + config['host']['remote']['user'] + '/' + remote_database_dump_file_name)
    sftp.remove('/home/' + config['host']['remote']['user'] + '/' + remote_database_dump_file_name + '.tar.gz')
    sftp.close()

def remove_temporary_data_dir():
    if os.path.exists(default_local_sync_path):
        shutil.rmtree(default_local_sync_path)
        _print(subject.LOCAL, 'Cleaning up', True)

#
# SSH UTILITY
#
def get_ssh_client():
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname = config['host']['remote']['host'], username = config['host']['remote']['user'], password = remote_ssh_password, compress = True)
    _print(subject.REMOTE, 'Successfully connect to SSH client (' + config['host']['remote']['host'] + ')', True)
    return ssh_client

def run_ssh_command(command):
    stdin, stdout, stderr = ssh_client.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()

    err = stderr.read().decode()
    if err and 0 != exit_status:
        sys.exit(_print(subject.ERROR, err, False))
    elif err:
        _print(subject.WARNING, err, True)

    return stdout

def download_status(sent,size):
    sent_mb=round(float(sent)/1024/1024,1)
    size=round(float(size)/1024/1024,1)
    sys.stdout.write(bcolors.PURPLE + "[REMOTE]" + bcolors.ENDC + " Status: {0} MB of {1} MB downloaded".
        format(sent_mb, size,))
    sys.stdout.write('\r')

#
# SYSTEM UTILITY
#
class bcolors:
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLACK = '\033[90m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class subject:
    INFO = bcolors.GREEN + '[INFO]' + bcolors.ENDC
    LOCAL = bcolors.BLUE + '[LOCAL]' + bcolors.ENDC
    REMOTE = bcolors.PURPLE + '[REMOTE]' + bcolors.ENDC
    ERROR = bcolors.RED + '[ERROR]' + bcolors.ENDC
    WARNING = bcolors.YELLOW + '[WARNING]' + bcolors.ENDC

def _print(header,message,do_print):
    if do_print:
        print(header + ' ' + message)
    else:
        return header + ' ' + message

#
# MAIN
#
if __name__ == "__main__":
   main()
