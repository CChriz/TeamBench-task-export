class APIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")


def parse_error_response(response) -> APIError:
    if response.status_code == 422:
        data = response.json()
        errors = data.get("errors", ["Unknown error"])
        return APIError(422, " ".join(errors))
    return APIError(response.status_code, "HTTP error")
