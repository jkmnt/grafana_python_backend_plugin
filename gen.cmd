python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. backend.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. health.proto

gcc fake.c -o fake_windows_amd64.exe
