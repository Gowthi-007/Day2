def format_api_success(data: dict) -> dict:
	"""Return a standard API success response wrapping the provided data.

	Args:
		data: The payload to include in the response.

	Returns:
		A dict with a status key and the provided data under the data key.
	"""
	return {"status": "success", "data": data}
