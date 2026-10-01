@echo off
cd /d "C:\Users\NEPAL\OneDrive\Desktop\QuantumHub"
git add -A
git status --short
echo --- committing ---
git commit -m "QuantumHub: quantum computing research index with tested simulator and algorithms"
echo --- pushing ---
git branch -M main
git push -u origin main --force
echo --- done ---
pause
