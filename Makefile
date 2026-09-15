setup:
	pip install -r requirements.txt

run:
	python app.py

test:
	python check.py

verify: test
	python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read()); print('syntax OK')"
