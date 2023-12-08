import concurrent.futures
import datetime
import os
import pprint

from bson import ObjectId
from pathlib import Path

from app.config import Config
from app.models.mongoClient import MongoClient
from app.services.elasticService import ElasticService
from app.utils.common import Common
from app.utils.pipeline import PipelineStages
from app.utils.presentationmanager import PresentationManager
from app.utils.socket import socket_error, socket_info, socket_success

pp = pprint.PrettyPrinter(depth=6) 

class MyDocumentsService:  

	@staticmethod
	def upload_document(logged_in_user, file, path):
		"""
		The `upload_document` function uploads a file to a specified path, parses and inserts the
		document into a database, updates the virtual filename, and saves the file on disk or a cloud
		bucket.
		
		Args:
		  logged_in_user: The logged_in_user parameter is an object that represents the currently logged
		in user. It contains information about the user, such as their ID, name, email, etc.
		  file: The `file` parameter is the file object that is being uploaded. It contains the actual
		file data and metadata such as the filename.
		  path: The `path` parameter represents the directory path where the document should be
		uploaded. It is a string that specifies the location within the file system or cloud storage
		where the document should be saved.
		
		Returns:
		  a tuple containing two values: 1) an integer indicating the success or failure of the upload
		process (1 for success, 0 for failure), and 2) the inserted ID of the document in the database.
		"""
		user_id = str(logged_in_user["_id"])
		if not user_id:
			raise Exception("User ID is missing")
		
		filename = Path(file.filename)
		new_path = Path(user_id) / Path(path)
		file_extension = filename.suffix.strip(".")
		new_path = str(new_path)
		print(f"New path: {new_path}")
		print(f"File: {filename}")
		print(f"File extension: {file_extension}")

		if file_extension not in ["pptx"]:
			socket_info(
				user_id,
				f"Skipping upload of {filename} due to incompatible file format",
			)
			return 0, None

		# Parse and insert document into database
		inserted_id = MyDocumentsService().parse_document(
			logged_in_user, file, new_path
		)

		if not inserted_id:
			socket_error(
				user_id,
				f"Failed to save {filename} to database due to some error...",
			)
			return 0, None

		# Update the virtual filename of the file based on its inserted ID
		update_response = MyDocumentsService().update_virtual_filename(
			inserted_id, file_extension
		)

		# Save file on disk or cloud bucket
		MyDocumentsService().save_file(file, inserted_id, logged_in_user, path)
		
		return 1, inserted_id           


	@staticmethod
	def upload_documents(logged_in_user, files, path):
		"""
		The function `upload_documents` uploads multiple files to a specified path, using a
		ThreadPoolExecutor to execute the upload process concurrently, and updates the document
		vectorstore for each successfully uploaded file.
		
		Args:
		  logged_in_user: The logged_in_user parameter is the user object of the currently logged in
		user. It contains information about the user, such as their ID, name, email, etc.
		  files: The `files` parameter is a list of files that you want to upload. Each file should be
		in a format that can be processed by the `upload_document` method of the `MyDocumentsService`
		class.
		  path: The `path` parameter is the directory path where the documents will be uploaded to.
		"""
		user_id = str(logged_in_user["_id"])
		print("User:", user_id)
		
		# Create a ThreadPoolExecutor with a specified number of threads (e.g., 4)
		with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
			# Submit the function with arguments to the thread pool
			results = [executor.submit(MyDocumentsService().upload_document, logged_in_user, file, path) for file in files]
		
		# Getting function returns from all function calls from threadpool
		outputs = [result.result() for result in results]
		# All document _ids inserted
		uploaded_documents_ids = [output[1] for output in outputs if output[1]]
		# Number of documents successfully uploaded
		uploaded_documents_num = sum([output[0] for output in outputs])
		
		
		# Calculating number of documents successfully uploaded
		if uploaded_documents_num > 0:
			socket_success(
				user_id, f"Successfully uploaded {uploaded_documents_num} documents!"
			)


	def parse_document(self, logged_in_user, file, new_path):
		"""
		The function `parse_document` takes in a logged-in user, a file, and a new path, and based on
		the file extension, it calls different parsing functions to process the file and returns an
		inserted ID.

		Args:
		  logged_in_user: The logged_in_user parameter is the user who is currently logged in and
		performing the document parsing operation.
		  file: The `file` parameter is the file object that represents the document to be parsed. It is
		passed to the `parse_document` method as an argument.
		  new_path: The `new_path` parameter is the path where the parsed document will be saved. It
		specifies the location where the parsed document will be stored after it has been processed.

		Returns:
		  the variable "inserted_id".
		"""
		try:
			filename = file.filename
			file_extension = filename.rsplit(".", 1)[-1]

			# PPT
			if file_extension == "pptx":
				print("Parsing pptx...")
				inserted_id = self._parse_pptx(file, filename, logged_in_user, new_path)

			else:
				print("Failed to parse invalid file format...")
				inserted_id = None

			return inserted_id

		except Exception as e:
			Common.exception_details("myDocumentsService.parse_document", e)
			return None

	def update_virtual_filename(self, file_id, file_extension):
		"""
		Updates the virtual filename of the given file to "file_id.file_extension"
		"""
		m_db = MongoClient.connect()

		virtual_filename = file_id + "." + file_extension
		response = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].update_one(
			{"_id": ObjectId(file_id)}, {"$set": {"virtualFileName": virtual_filename}}
		)
		return response.modified_count


	def get_file(self, file_id):
		"""
		The function `get_file` retrieves a file from a MongoDB database based on its ID.

		Args:
		  file_id: The `file_id` parameter is the unique identifier of the file that you want to
		retrieve from the database.

		Returns:
		  the first document that matches the given file_id.
		"""
		m_db = MongoClient.connect()

		pipeline = [
			PipelineStages.stage_match({"_id": ObjectId(file_id)})
		] + MyDocumentsService._get_my_documents_pipeline()

		response = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].aggregate(pipeline)

		return Common.cursor_to_dict(response)[0]


	def get_file_by_virtual_name(self, virtual_name):
		"""
		The function retrieves a document from a MongoDB collection based on its virtual file name.

		Args:
		  virtual_name: The virtual name is a parameter that represents the name of the file you want to
		retrieve from the database.

		Returns:
		  the document that matches the given virtual name from the specified collection in the MongoDB
		database.
		"""
		m_db = MongoClient.connect()

		document = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].find_one(
			{"virtualFileName": virtual_name}
		)

		return document

	def save_file(self, original_file, file_id, user, path):
		"""
		The `save_file` function saves a file either to a cloud storage bucket or to a local folder,
		depending on the value of the `PRODUCTION_CHECK` variable.

		Args:
		  original_file: The original file that needs to be saved.
		  file_id: The `file_id` parameter is the unique identifier of the file that needs to be saved.
		It is used to retrieve information about the file from the database.
		  user: The "user" parameter is a dictionary that contains information about the user. It likely
		includes details such as the user's ID, name, email, and other relevant information.
		  path: The `path` parameter is a string that represents the path where the file should be
		saved. It can be an absolute path or a relative path.
		"""
		key = "_id"
		user_id = user[key]
		# Get virtual filename from DB
		file = self.get_file(file_id)
		virtual_file_name = file["virtualFileName"]
		file_root = file["root"]

		if Config.GCP_PROD_ENV:
			pass
			# # print("PATH : ", path)
			# # print("Original file :", original_file)

			# if path == "/":
			#     folder_name = str(user_id) + path
			# else:
			#     folder_name = file_root[1:] + "/"

			# bucket = Production.get_users_bucket()
			# file_blob = bucket.blob(folder_name + virtual_file_name)

			# # finding the file extension
			# extension = virtual_file_name[virtual_file_name.rfind(".") + 1 :]

			# original_file.stream.seek(0)
			# if extension == "pdf":
			#     file_blob.upload_from_string(
			#         original_file.read(), content_type="application/pdf"
			#     )
			# else:
			#     file_blob.upload_from_string(original_file.read())

			# print(f"File {virtual_file_name} uploaded to {folder_name} successfully.")
			# print("Path sent to get_file_save_path: ", path)

		else:
			# Ensure that the user image upload folder exists
			folder_path = os.path.join(Config.USER_FOLDER, str(user_id))
			os.makedirs(folder_path, exist_ok=True)

			# Save file
			file_save_path = self.get_file_save_path(virtual_file_name, user_id, path)
			print(type(original_file))
			original_file.stream.seek(0)
			original_file.save(file_save_path)

			print("Saved file!")


	@staticmethod
	def _get_my_documents_pipeline():
		"""Common My Documents pipeline

		Returns:
			list: Common My Documents pipeline
		"""

		my_documents_pipeline = [
			PipelineStages.stage_add_fields(
				{
					"createdBy._id": {"$toString": "$createdBy._id"},
					"createdOn": {"$dateToString": {"date": "$createdOn"}},
					"_id": {"$toString": "$_id"},
					"virtualFileName": "$virtualFileName",
					"usersWithAccess": {
						"$map": {
							"input": "$usersWithAccess",
							"as": "user",
							"in": {"$toString": "$$user"},
						}
					},
				}
			),
			PipelineStages.stage_unset(["embeddings", "highlightsSummary"]),
		]

		return my_documents_pipeline

	@staticmethod
	def _create_my_document_db_struct(title, description, filename, user, root):
		"""
		The function `_create_my_document_db_struct` creates a document structure for a file in a
		document database.

		Args:
		  title: The title of the document.
		  description: The "description" parameter is a string that represents the description of the
		document. It provides additional information or details about the document.
		  filename: The `filename` parameter is the name of the file that you want to create a document
		database structure for.
		  user: The "user" parameter is a dictionary that represents the user who is creating the
		document. It contains information about the user, such as their ID and a reference to the user
		object.
		  root: The "root" parameter is used to specify the root directory or folder where the document
		will be stored. If no root directory is provided (root == ""), the document will be stored in
		the root directory ("/").

		Returns:
		  a document (doc) with various fields such as title, description, itemizedSummary,
		highlightsSummary, originalFileName, virtualFileName, createdBy, createdOn, embeddings, type,
		root, usersWithAccess, and storedOnCloud.
		"""
		if root == "":
			root = "/"

		m_db = MongoClient.connect()
		# Check if the file with the same name already exists in the collection
		existing_files = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].find(
			{"root": str(root)},
			{"_id": 0, "originalFileName": 1}
		)

		# Create a set of existing filenames for efficient lookup
		existing_filenames = set(file["originalFileName"] for file in existing_files)

		# If the filename already exists, increment the index count
		index = 1
		new_filename = filename
		while new_filename in existing_filenames:
			file_name_without_extension, file_extension = os.path.splitext(filename)
			print("File name without extension:", file_name_without_extension)
			new_filename = f"{file_name_without_extension}({index}){file_extension}"
			index = index + 1

		doc = {
			"title": title,
			"description": description,
			"itemizedSummary": "",  # update when itemized summary of this record is generated
			"highlightsSummary": "",  # update when highlight summary of this record is generated
			"originalFileName": str(new_filename),  # Use the unique filename
			"virtualFileName": "",
			"createdBy": {"_id": ObjectId(user["_id"]), "ref": "user"},
			"createdOn": datetime.datetime.utcnow(),
			"embeddings": None,
			"type": "File",
			"root": root,
			"usersWithAccess": [],
		}

		return doc

	@staticmethod
	def _create_my_ppt_index_struct(slide_content, filename, user_id, root, virtual_filename):
		docs = []
		common_values = {
				"user_id": user_id,
				"root": root,
				"virtualFileName": virtual_filename,
				"originalFileName": filename,                
			}
		for slide in slide_content:
			slide.update(common_values)
		docs.extend(slide_content)
		return docs


	def _parse_pptx(self, file, filename, user, root):
		"""
		The _parse_pptx function extracts content from the file and inserts a new record corresponding to the file.
			Args:
				file (file storage) : The file to be parsed
				original_filename (str) : The name of this file to be parsed
				user (dict): Identifies the user uploading the file.

		Args:
			self: Represent the instance of the class
			file : The file to be parsed
			original_filename (str) : The name of this file to be parsed
			user (str): Corresponds to the user uploading the file.

		Returns:
			The Objectid of the newly inserted record
			:param user:
			:param file:
			:param filename:

		"""

		m_db = MongoClient.connect()


		ppt = PresentationManager(file=file)
		slide_texts = ppt.extract_all_text()
		title = ppt.title
		ppt_content = "\n".join([slide["content"] for slide in slide_texts if slide["content"]])

		file_data = MyDocumentsService._create_my_document_db_struct(
			title, ppt_content, filename, user, root
		)
		# print(file_data)
		response = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].insert_one(file_data)

		if response:
			if response.inserted_id:
				virtual_filename = str(response.inserted_id) + ".pptx"
				docs = MyDocumentsService._create_my_ppt_index_struct(
					slide_content=slide_texts,
					filename=file_data["originalFileName"],
					user_id=user["_id"],
					root=root,
					virtual_filename=virtual_filename
				)
				success, errors = ElasticService().index_batch(docs=docs)
				print(f"\nIndexed: {success} documents \nErrors: {len(errors)}")


			return str(response.inserted_id)

		return None

	@staticmethod
	def generate_pptx_from_search(elastic_results, query, user_id):
		try:
			ppt_paths = {}
			user_folder = os.path.join(Config.USER_FOLDER, str(user_id))
			# Get save paths for all presentations
			for item in elastic_results:
				virtual_filename = item['virtualFileName']
				if virtual_filename not in ppt_paths:
					file_root = item['root']
					file_path = os.path.join(user_folder, file_root[1:], virtual_filename)
					ppt_paths[virtual_filename] = file_path

			# Ensure that the folder exists
			folder_path = os.path.join(user_folder, Config.GENERATED_FOLDER_NAME)
			os.makedirs(folder_path, exist_ok=True)
			dest_filepath = os.path.join(folder_path, f"{query}.pptx")
			
			# Combine all slides into single presentation			
			for slide in elastic_results:
				slides_to_copy = [slide['slide_index']]
				virtual_filename = slide['virtualFileName']
				source = PresentationManager(ppt_paths[virtual_filename])

				PresentationManager.copy_slide_to_other_presentation(
					source=source,
					dest_filepath=dest_filepath,
					slides_to_copy=slides_to_copy
				)
			
			return dest_filepath		

		except Exception as e:
			Common.exception_details("myDocumentsService.generate_pptx_from_search", e)
			return None		
				  