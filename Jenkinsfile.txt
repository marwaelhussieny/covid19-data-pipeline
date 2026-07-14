pipeline {
    agent any

    environment {
        IMAGE_NAME = 'covid19-data-pipeline'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Lint') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --no-cache-dir -r requirements.txt
                    ruff check src/ tests/ dags/
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    . .venv/bin/activate
                    pytest tests/ -v
                '''
            }
        }

        stage('Build Docker Images') {
            steps {
                sh '''
                    docker build -f Dockerfile.airflow -t ${IMAGE_NAME}-airflow:${BUILD_NUMBER} .
                    docker build -f Dockerfile.dashboard -t ${IMAGE_NAME}-dashboard:${BUILD_NUMBER} .
                '''
            }
        }
    }

    post {
        success {
            echo "Pipeline succeeded: build, tests, and Docker images all passed."
        }
        failure {
            echo "Pipeline failed - check the stage logs above."
        }
        always {
            sh 'rm -rf .venv'
        }
    }
}