from typing import Union

from bson import ObjectId

from app import socketio

# On connection


@socketio.on("connect")
def connect():
    """
    The connect function is used to connect the socket to a remote address.
    The function takes no arguments and returns nothing.

    Args:

    Returns:
        Nothing.
    """
    try:
        print("Socket Connected!")
    except Exception as e:
        print("Error: ", e)


# On disconnection


@socketio.on("disconnect")
def disconnect():
    """
    The disconnect function is used to disconnect the socket from the server.

    Args:

    Returns:
        Nothing.
    """
    try:
        print("Socket Disconnected!")
    except Exception as e:
        print("Error: ", e)


# Common socket events


# Error
def socket_error(userid: Union[str, ObjectId], msg: str) -> None:
    print(f"🔌 socket_error: {msg}")
    socketio.emit(f"{userid}_error", msg)


# Success
def socket_success(userid: Union[str, ObjectId], msg: str) -> None:
    print(f"🔌 socket_success: {msg}")
    socketio.emit(f"{userid}_success", msg)


# Info
def socket_info(userid: Union[str, ObjectId], msg: str) -> None:
    print(f"🔌 socket_info: {msg}")
    socketio.emit(f"{userid}_info", msg)
