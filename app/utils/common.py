"""
    Common functions accessible throughout the application
"""
import json
import re
import os
import traceback

from bson import json_util
from typing import Any
from urllib.parse import urlsplit
from werkzeug.security import generate_password_hash, check_password_hash

from app.config import Config
from app.models.mongoClient import MongoClient


class Common:
    
    @staticmethod
    def exception_details(function_name, exception):
        """
        The function "exception_details" prints the details of an exception, including the function
        name, exception details, and traceback information.
        
        Args:
          function_name: The name of the function where the exception occurred.
          exception: The exception parameter is the exception object that was raised during the
        execution of the function. It contains information about the type of exception and any
        additional details that may be available.
        """
        # code to handle the exception
        print("=====================================================================================")
        print("⚠️ Exception in function: ", function_name)
        print("-------------------------------------------------------------------------------------")
        print("Exception details:", exception)
        print("-------------------------------------------------------------------------------------")
        print("Traceback information:")
        traceback.print_exc()
        print("=====================================================================================")

    @staticmethod
    def allowed_file(filename):
        """Check if a file is an allowed file based on a set of allowed image extensions

        Args:
            filename (str): filename

        Returns:
            boolean: Returns the status of whether the file is an allowed file or not
        """

        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_IMAGE_EXTENSIONS

    @staticmethod
    def get_file_extension(filename):
        """Get the extension of a file

        Args:
            filename (str): The filename of the file whose extension is to be extracted

        Returns:
            str: The extension of the file
        """
        return filename.split('.')[-1]


    @staticmethod
    def cursor_to_dict(cursor):
        """Converts a cursor to python dictionary

        Args:
            cursor (Cursor): Cursor Object

        Returns:
            dict: Python dictionary representation of input Cursor
        """

        try:

            # iterate over cursor to get a list of dicts
            cursor_dict = [doc for doc in cursor]

            # serialize to json string
            cursor_dict_string = json.dumps(cursor_dict, default=json_util.default)

            # json from json string
            cursor_dict = json.loads(cursor_dict_string)

            return cursor_dict

        except Exception as e:
            Common.exception_details("common.py : cursor_to_dict", e)

    @staticmethod
    def process_response(response):
        """Converts a response object to python dictionary and avoid type errors

            Args:
                response (dict): Response object

            Returns:
                dict: Python dictionary representation of input Response
        """

        processed_response = json.loads(json_util.dumps(response, default=str))

        return processed_response

    @staticmethod
    def get_field_value_or_default(dictionary: dict, field_name: str, default_value: Any) -> Any:
        """Returns the value of a field from a dict or the default value specified

        Args:
            dictionary(dict): the dictionary from which fields will be fetched
            field_name(str): name of the field
            default_value(Any): The default value to be returned if the field is not found

        Returns:
            The value of the field in the dict if found, or the default_value
        """

        if field_name in dictionary.keys():
            return dictionary[field_name]
        else:
            return default_value

    @staticmethod
    def get_valid_filename(name):
        """
        modified from: https://github.com/django/django/blob/main/django/utils/text.py

        Return the given string converted to a string that can be used for a clean
        filename. Remove leading and trailing spaces; convert other spaces to
        underscores; and remove anything that is not an alphanumeric, dash,
        underscore, or dot.
        >>> get_valid_filename("john's portrait in 2004.jpg")
        'johns_portrait_in_2004.jpg'
        """
        name = str(name).strip()
        file_name, file_extension = os.path.splitext(name)
        file_name = file_name.rstrip(". ").replace(" ", "_")
        file_name = re.sub(r"(?u)[^-\w.]", "", file_name)
        max_name_lenght = 255 - len(file_extension)
        final_name = file_name[:max_name_lenght] + file_extension

        if final_name in {"", ".", ".."}:
            raise Exception("Could not derive file name from '%s'" % name)
        
        return final_name      