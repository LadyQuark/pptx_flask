"""
    Common responses used throughout the application, with provisions for 
    creating custom response within a specified structure
"""

import datetime
import json

from bson import ObjectId
from flask import jsonify

from app import socketio
from app.utils.messages import Messages


class Response:
    @staticmethod
    def custom_response(data="", message="", success=True, status=200):
        """Generates a custom response

        Args:
            data (str, optional): Data to pass in the response. Defaults to "".
            message (str, optional): Response message. Defaults to "".
            success (bool, optional): Response indicating success of api call. Defaults to True.
            status (int, optional): Http status code. Defaults to 200.

        Returns:
            json: Custom response
        """
        return jsonify({"data": data, "message": message, "success": success}), status

    @staticmethod
    def socket_reponse(
        event: str,
        data: any = [],
        message: str = "",
        success: bool = True,
        status: int = 200,
    ) -> None:
        """
        The function `socket_reponse` emits a socket event with a message, data, success status, and
        status code.

        Args:
          event (str): The event parameter is a string that represents the name of the event that you
        want to emit to the socket clients.
          data (any): The `data` parameter is used to pass any data that you want to send along with the
        socket response. It can be of any type, such as a string, integer, list, dictionary, etc.
          message (str): The "message" parameter is a string that represents a message or description
        related to the response. It can be used to provide additional information or context about the
        response.
          success (bool): The "success" parameter is a boolean value that indicates whether the
        operation was successful or not. It is set to True by default. Defaults to True
          status (int): The `status` parameter is an integer that represents the HTTP status code of the
        response. It is set to 200 by default, which indicates a successful response. However, you can
        change it to any other valid HTTP status code based on your requirements. Defaults to 200
        """
        socketio.emit(
            event,
            {"message": message, "data": data, "success": success, "status": status},
        )

    @staticmethod
    def unauthorized():
        """Generates an unauthorized response

        Returns:
            json: Unauthorized response(401)
        """
        return (
            jsonify({"data": [], "message": Messages.UNAUTHORIZED, "success": False}),
            401,
        )

    @staticmethod
    def missing_parameters():
        """Generates a response for missing parameters

        Returns:
            json: Response for missing parameters(400)
        """
        return (
            jsonify(
                {
                    "data": [],
                    "message": Messages.MISSING_REQUIRED_PARAMETERS,
                    "success": False,
                }
            ),
            400,
        )

    @staticmethod
    def missing_required_parameter(param=""):
        """Generates a response for a missing parameter

        Returns:
            json: Response for a missing parameter(400)
        """
        return (
            jsonify(
                {
                    "data": [],
                    "message": Messages.MISSING_REQUIRED_PARAMETER + str(param),
                    "success": False,
                }
            ),
            400,
        )

    @staticmethod
    def server_error():
        """Generates a response for server error

        Returns:
            json: Response for internal server error(500)
        """
        return (
            jsonify(
                {
                    "data": [],
                    "message": Messages.ERROR_INTERNAL_SERVER,
                    "success": False,
                }
            ),
            500,
        )


# custom JSON encoder that allows serialization of ObjectId and datetime


# The class JSONEncoder is a subclass of json.JSONEncoder that provides custom encoding for JSON
# objects.
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        """
        The function converts ObjectId and datetime objects to strings, and uses the default JSONEncoder
        for other objects.

        Args:
          o: The parameter "o" is the object that needs to be encoded into JSON format.

        Returns:
          The code is returning a string representation of the object if it is an instance of ObjectId
        or datetime.datetime. If the object is not of these types, it will call the default method of
        the JSONEncoder class to handle the serialization.
        """
        if isinstance(o, ObjectId) or isinstance(o, datetime.datetime):
            return str(o)
        return json.JSONEncoder.default(self, o)
