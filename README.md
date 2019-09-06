

Windows Setup
=============
```
git clone https://github.com/dwoz/stats-graphs.git
cd stats-graphs
.\get-rrdtool.bat
c:\python27\Scripts\virtualenv.exe venv
.\venv\Scripts\activate
pip install -r requirements.txt
python .\process_memory.py 1304 --children
```
