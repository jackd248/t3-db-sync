#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from db_sync_tool.utility import parser, mode, system, helper, output
from db_sync_tool.database import utility


def create_origin_database_dump():
    """
    Creating the origin database dump file
    :return:
    """
    if not mode.is_import():
        parser.get_database_configuration(mode.Client.ORIGIN)
        utility.generate_database_dump_filename()
        helper.check_and_create_dump_dir(mode.Client.ORIGIN, helper.get_dump_dir(mode.Client.ORIGIN))

        _dump_file_path = helper.get_dump_dir(mode.Client.ORIGIN) + utility.database_dump_file_name

        output.message(
            output.Subject.ORIGIN,
            'Creating database dump',
            True
        )
        mode.run_command(
            helper.get_command('origin', 'mysqldump') + ' --no-tablespaces ' +
            utility. generate_mysql_credentials('origin') + ' ' +
            system.config['origin']['db']['name'] + ' ' +
            utility.generate_ignore_database_tables() +
            ' > ' + _dump_file_path,
            mode.Client.ORIGIN
        )

        utility.check_database_dump(mode.Client.ORIGIN, _dump_file_path)
        prepare_origin_database_dump()


def import_database_dump():
    """
    Importing the selected database dump file
    :return:
    """
    if (not system.option['is_same_client'] and not mode.is_import()):
        prepare_target_database_dump()

    if not system.option['keep_dump'] and not system.option['is_same_client']:
        output.message(
            output.Subject.TARGET,
            'Importing database dump',
            True
        )

        if not mode.is_import():
           _dump_path = helper.get_dump_dir(mode.Client.TARGET) + utility.database_dump_file_name
        else:
           _dump_path = system.option['import']

        utility.check_database_dump(mode.Client.TARGET, _dump_path)
        mode.run_command(
            helper.get_command('target', 'mysql') + ' ' + utility.generate_mysql_credentials('target') + ' ' +
            system.config['target']['db']['name'] + ' < ' + _dump_path,
            mode.Client.TARGET
        )


def prepare_origin_database_dump():
    """
    Preparing the origin database dump file by compressing them as .tar.gz
    :return:
    """
    output.message(
        output.Subject.ORIGIN,
        'Compressing database dump',
        True
    )
    mode.run_command(
        helper.get_command(mode.Client.ORIGIN, 'tar') + ' cfvz ' + helper.get_dump_dir(
            mode.Client.ORIGIN) + utility.database_dump_file_name + '.tar.gz -C ' + helper.get_dump_dir(
            mode.Client.ORIGIN) + ' ' + utility.database_dump_file_name + ' > /dev/null',
        mode.Client.ORIGIN
    )


def prepare_target_database_dump():
    """
    Preparing the target database dump by the unpacked .tar.gz file
    :return:
    """
    output.message(output.Subject.TARGET, 'Extracting database dump', True)
    mode.run_command(
        helper.get_command('target', 'tar') + ' xzf ' + helper.get_dump_dir(
            mode.Client.TARGET) + utility.database_dump_file_name + '.tar.gz -C ' + helper.get_dump_dir(
            mode.Client.TARGET) + ' > /dev/null',
        mode.Client.TARGET
    )
