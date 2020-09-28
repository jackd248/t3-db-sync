#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from utility import system, output, connect


#
# GLOBALS
#

class SyncMode:
    DUMP_LOCAL = 'DUMP_LOCAL'
    DUMP_REMOTE = 'DUMP_REMOTE'
    IMPORT_LOCAL = 'IMPORT_LOCAL'
    IMPORT_REMOTE = 'IMPORT_REMOTE'
    RECEIVER = 'RECEIVER'
    SENDER = 'SENDER'
    PROXY = 'PROXY'


class Client:
    ORIGIN = 'origin'
    TARGET = 'target'


# Default sync mode
sync_mode = SyncMode.RECEIVER

#
# FUNCTIONS
#

def get_sync_mode():
    """
    Returning the sync mode
    :return: String sync_mode
    """
    return sync_mode

def check_sync_mode():
    """
    Checking the sync_mode based on the given configuration
    :return: String subject
    """
    global sync_mode

    if 'host' in system.config['host']['origin']:
        sync_mode = SyncMode.RECEIVER
        _description = output.CliFormat.BLACK + '(REMOTE --> LOCAL)' + output.CliFormat.ENDC
    if 'host' in system.config['host']['target']:
        sync_mode = SyncMode.SENDER
        _description = output.CliFormat.BLACK + '(LOCAL --> REMOTE)' + output.CliFormat.ENDC
    if 'host' in system.config['host']['origin'] and 'host' in system.config['host']['target']:
        sync_mode = SyncMode.PROXY
        _description = output.CliFormat.BLACK + '(REMOTE --> LOCAL --> REMOTE)' + output.CliFormat.ENDC
    if not 'host' in system.config['host']['origin'] and not 'host' in system.config['host']['target']:
        sync_mode = SyncMode.DUMP_LOCAL
        _description = output.CliFormat.BLACK + '(LOCAL, NO TRANSFER/IMPORT)' + output.CliFormat.ENDC
        system.option['is_same_client'] = True
    if 'host' in system.config['host']['origin'] and 'host' in system.config['host']['target'] and system.config['host']['origin']['host'] == system.config['host']['target']['host']:
        if ('port' in system.config['host']['origin'] and 'port' in system.config['host']['target'] and system.config['host']['origin']['port'] == system.config['host']['target']['port']) or ('port' not in system.config['host']['origin'] and 'port' not in system.config['host']['target']):
            sync_mode = SyncMode.DUMP_REMOTE
            _description = output.CliFormat.BLACK + '(REMOTE, NO TRANSFER/IMPORT)' + output.CliFormat.ENDC
            system.option['is_same_client'] = True
    if system.option['import'] != '':
        output.message(
            output.Subject.INFO,
            'Import file: ' + system.option['import'],
            True
        )
        if 'host' in system.config['host']['target']:
            sync_mode = SyncMode.IMPORT_REMOTE
            _description = output.CliFormat.BLACK + '(REMOTE, NO TRANSFER)' + output.CliFormat.ENDC
        else:
            sync_mode = SyncMode.IMPORT_LOCAL
            _description = output.CliFormat.BLACK + '(LOCAL, NO TRANSFER)' + output.CliFormat.ENDC

    output.message(
        output.Subject.INFO,
        'Sync mode: ' + sync_mode + ' ' + _description,
        True
    )


def is_remote(client):
    """
    Check if given client is remote client
    :param client: String
    :return: Boolean
    """
    if client == Client.ORIGIN:
        return is_origin_remote()
    elif client == Client.TARGET:
        return is_target_remote()


def is_target_remote():
    """
    Check if target is remote client
    :return: Boolean
    """
    return sync_mode == SyncMode.SENDER or sync_mode == SyncMode.PROXY or sync_mode == SyncMode.DUMP_REMOTE or sync_mode == SyncMode.IMPORT_REMOTE

def is_origin_remote():
    """
    Check if origin is remote client
    :return: Boolean
    """
    return sync_mode == SyncMode.RECEIVER or sync_mode == SyncMode.PROXY or sync_mode == SyncMode.DUMP_REMOTE or sync_mode == SyncMode.IMPORT_REMOTE


def is_import():
    """
    Check if sync mode is import
    :return: Boolean
    """
    return sync_mode == SyncMode.IMPORT_LOCAL or sync_mode == SyncMode.IMPORT_REMOTE


def run_command(command, client, force_output=False):
    """
    Check if target is remote client
    :param command: String
    :param client: String
    :param force_output: Boolean
    :return:
    """
    # @ToDo: Code duplication
    if client == Client.ORIGIN:
        if system.option['verbose']:
            output.message(
                output.Subject.ORIGIN,
                output.CliFormat.BLACK + command + output.CliFormat.ENDC,
                True
            )
        if is_origin_remote():
            if force_output:
                return ''.join(connect.run_ssh_command_origin(command).readlines())
            else:
                return connect.run_ssh_command_origin(command)
        else:
            if force_output:
                return os.popen(command).read()
            else:
                return os.system(command)
    elif client == Client.TARGET:
        if system.option['verbose']:
            output.message(
                output.Subject.TARGET,
                output.CliFormat.BLACK + command + output.CliFormat.ENDC,
                True
            )
        if is_target_remote():
            if force_output:
                return ''.join(connect.run_ssh_command_target(command).readlines())
            else:
                return connect.run_ssh_command_target(command)
        else:
            if force_output:
                return os.popen(command).read()
            else:
                return os.system(command)
