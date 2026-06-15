from flask import jsonify

def register_error_handlers(app):
    @app.errorhandler(400)
    def handle_400(error):
        response = jsonify({'error': 'Bad Request', 'message': 'The request could not be understood or was missing required parameters.'})
        response.status_code = 400
        return response

    @app.errorhandler(401)
    def handle_401(error):
        response = jsonify({'error': 'Unauthorized', 'message': 'Authentication is required and has failed or has not yet been provided.'})
        response.status_code = 401
        return response

    @app.errorhandler(403)
    def handle_403(error):
        response = jsonify({'error': 'Forbidden', 'message': 'You do not have permission to access this resource.'})
        response.status_code = 403
        return response

    @app.errorhandler(404)
    def handle_404(error):
        response = jsonify({'error': 'Not Found', 'message': 'The requested resource could not be found.'})
        response.status_code = 404
        return response

    @app.errorhandler(405)
    def handle_405(error):
        response = jsonify({'error': 'Method Not Allowed', 'message': 'The method is not allowed for the requested URL.'})
        response.status_code = 405
        return response

    @app.errorhandler(409)
    def handle_409(error):
        response = jsonify({'error': 'Conflict', 'message': 'The request could not be completed due to a conflict with the current state of the target resource.'})
        response.status_code = 409
        return response

    @app.errorhandler(500)
    def handle_500(error):
        response = jsonify({'error': 'Internal Server Error', 'message': 'An unexpected error occurred.'})
        response.status_code = 500
        return response

    @app.errorhandler(Exception)
    def handle_default(error):
        response = jsonify({'error': 'Unexpected Error', 'message': str(error)})
        response.status_code = 500
        return response
