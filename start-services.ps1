# Start RAG Service and Main Backend

Write-Host "--- Crypto Knowledge System ---" -ForegroundColor Cyan
Write-Host "Streamlit UI: http://localhost:8501" -ForegroundColor Cyan
Write-Host "API Backend: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Ingestion Service: http://localhost:8012" -ForegroundColor Cyan
Write-Host "Storage Service: http://localhost:8013" -ForegroundColor Cyan
Write-Host "Healing Service: http://localhost:8014" -ForegroundColor Cyan
Write-Host "RAG Service: http://localhost:8011" -ForegroundColor Cyan
Write-Host "---------------------------------" -ForegroundColor Cyan

# Start Ingestion Service
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\myenv\Scripts\Activate.ps1; python services\ingestion-service\main.py"
Start-Sleep -Seconds 2

# Start Storage Service
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\myenv\Scripts\Activate.ps1; python services\storage-service\main.py"
Start-Sleep -Seconds 2

# Start Healing Service
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\myenv\Scripts\Activate.ps1; python services\healing-service\main.py"
Start-Sleep -Seconds 2

# Start Streamlit in background (it will open browser automatically)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\myenv\Scripts\Activate.ps1; streamlit run streamlit_app.py"

# Run Backend in this window
python app.py
