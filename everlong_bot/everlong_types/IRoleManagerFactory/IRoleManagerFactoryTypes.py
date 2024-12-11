"""Dataclasses for all structs in the IRoleManagerFactory contract.

DO NOT EDIT.  This file was generated by pypechain v0.0.49.
See documentation at https://github.com/delvtech/pypechain """

# super() call methods are generic, while our version adds values & types
# pylint: disable=arguments-differ

# contracts have PascalCase names
# pylint: disable=invalid-name

# contracts control how many attributes and arguments we have in generated code
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments

# unable to determine which imports will be used in the generated code
# pylint: disable=unused-import

# we don't need else statement if the other conditionals all have return,
# but it's easier to generate
# pylint: disable=no-else-return

# We import this contract itself to ensure all nested structs have a fully qualified name.
# We use this to avoid namespace collisions, as well as having a uniform
# type structure to do lookups when functions return these structs.
# pylint: disable=import-self


from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Project:
    """Project struct."""

    roleManager: str
    registry: str
    accountant: str
    debtAllocator: str