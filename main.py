from app import app, socketio

if __name__ == '__main__':
    # app.run(debug=True)
    
    # For local run
    # socketio.run(app, debug=True, host='0.0.0.0', port=5000, log_output=True)
    
    # For GCP
    socketio.run(app, debug=True, host='0.0.0.0', port=8080, log_output=True, allow_unsafe_werkzeug=True)
    
