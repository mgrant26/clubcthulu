"""
Module for working with callable objects.

This module provides utilities for working with callable objects in Python.

Classes:
    None

Functions:
    None

Constants:
    Callable: A type hint representing a callable object.
"""
from typing import Callable
from clienthandler import Client


class Command:
    """Command class

    wrapper for commands

    Parameters:
    name: str
        The name of the command, used to call the command
    clbk: Callable[[dict[str, any]], Client]
        The command that is run when the command is executed
    privilege_req: int
        Default: 0
        The required privilege level to execute this command
    *params: list[str]
        The parameter names for this command
    """

    def __init__(self, name: str, clbk: Callable[[dict[str, any]], Client],
                 *params: list[str], privilege_req: int = 0):
        self.name = name
        self._clbk = clbk
        self.privilege_req = privilege_req
        self.params = params

    def run(self, params: dict[str, any], executor: Client = None):
        """ Run command function
        Wrapper for the callback in order to enforce privilege requirements
        Parameters:
        params: dict[str, any]
            The parameters to use
        executor: Client
            Default: None
            Used to determine if the command can be run
        """
        if (self.privilege_req > 0 and executor is not None
                and self.privilege_req > executor.privilege_level):
            raise PermissionError("Insufficient permission to run command")
        return self._clbk(params, executor)

    @property
    def clbk(self):
        """
        Raises an AttributeError.

        Raises:
            AttributeError: This method raises an AttributeError if 
            the '_clbk' attribute is accessed.
        """
        raise AttributeError(
            "The variable '_clbk' is private and cannot be used outside of the Command Class")

    @clbk.setter
    def clbk(self, other):
        raise AttributeError("Cannot change '_clbk' is private.")


class CommandProcessor:
    """ Command Processor class
    used to parse command strings
    Parameters:
    initial_commands: list[Command]
        Default: []
        The initial list of commands that can be used, added to the command map
    initial_aliases: dict[str, str]
        Default: {}
        The initial map of command aliases
    """

    def __init__(self, initial_commands: list[Command] = None,
                 initial_aliases: dict[str, str] = None):
        self.commands = {
            e.name: e for e in initial_commands if initial_commands is not None}
        self.aliases = initial_aliases if initial_aliases is not None else {}

    def set_alias(self, name: str, alias: str):
        """ Sets an alias to a command name
        Parameters:
        name: str
            Name of the command
        alias: str
            Alias to use
        """
        self.aliases[alias] = name

    def add_command(self, command: Command):
        """ Adds a command to the command map
        Parameters:
        command: Command
            Command to add
        """
        self.commands[command.name] = command

    def run_command(self, name: str, param: dict[str, any], executor: Client = None):
        """ Executes a command
        Parameters:
        name: str
            Name of the command
        param: dict[str, any]
            Parameters to pass to the command
        executor: Client
            Default: None
            Client to use as executor
        """
        command = self.commands.get(name)
        if command is None:
            if (command := self.commands.get(self.aliases.get(name))) is None:
                return False
        command.run(param, executor)
        return True

    def parse_command(self, command_string: str, executor: Client = None) -> bool:
        """ Parses a command string and executes run_command
        Parameters:
        command_string: str
            The command string to process
        executor: Client
            Default: None
            Client to execute as
        """
        if not command_string:
            return False
        split_string = command_string.split()
        cmd_name = split_string[0].lower()
        return self.run_command(cmd_name, split_string[1:], executor)
