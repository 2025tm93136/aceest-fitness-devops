pipeline {
    agent any

    environment {
        IMAGE = "aceest-fitness"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Build & Lint') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install -r requirements-dev.txt
                    python -m py_compile app.py tests/*.py
                    flake8 .
                '''
            }
        }
        stage('Unit Tests') {
            steps {
                sh '''
                    . .venv/bin/activate
                    pytest -v --junitxml=test-results.xml
                '''
            }
        }
        stage('Docker Build') {
            steps {
                sh 'docker build --target test -t ${IMAGE}:test .'
                sh 'docker run --rm ${IMAGE}:test'
                sh 'docker build --target runtime -t ${IMAGE}:${BUILD_NUMBER} .'
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'test-results.xml'
            cleanWs()
        }
    }
}
