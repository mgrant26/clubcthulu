"""
Extra Vector functions
"""
from typing import TypeAlias
Vector: TypeAlias = list[float]  # Creates Vector as an alias for a float list


def add(one: Vector, two: Vector):
    """Adds two vectors
    Parameters:
    one: Vector
        First Vector
    two: Vector
        Second Vector
    """
    copy = one
    for i in range(0, len(copy)-1):
        copy[i] += two[i]
    return copy


def sub(one: Vector, two: Vector):
    """Subtracts two vectors
    Parameters:
    one: Vector
        First Vector
    two: Vector
        Second Vector
    """
    copy = one
    for i in range(0, len(copy)-1):
        copy[i] -= two[i]
    return copy


def scale(scalar: float, vector: Vector):
    """
    Scales a vector by a scalar.

    Args:
        scalar (float): The scalar value to scale the vector by.
        vector (List[float]): The vector to be scaled.

    Returns:
        List[float]: The scaled vector.
    """
    return [scalar * i for i in vector]


def equals(one: Vector, two: Vector):
    """
    Checks if two vectors are equal element-wise.

    Args:
        one (List[float]): The first vector.
        two (List[float]): The second vector.

    Returns:
        bool: True if the vectors are equal, False otherwise.
    """
    return one == two
