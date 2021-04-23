# grafana_python_backend_plugin

Experimental grafana backend plugin in python for supporting alerts.

Grafana pure JS datasource plugins are great for fetching data from the custom APIs.
The requests are fired straight from the browser or via the grafana built-in proxy.
Responses are processed in JS and converted to the Grafana-recognized dataframes.

Unfortunately such datasource plugins don't support alerting since alert engine is running in Grafana backend.
One can't have alerting engine in the browser )
The backend part of the datasource plugin is needed in order to support alerting.
The official way is to create the Go plugin with the still-in-development sdk https://github.com/grafana/grafana-plugin-sdk-go/ .

The backend Go code mostly wraps/unwraps/encodes/recodes all the stuff already existing in JS land.
There are a lot of unnecessary transformations and syncronizations in a way.

What if backend plugin could be built with just the minimal support of alerts ?
All other (normal) requests will be JS-based straight to the custom API.

Grafana alerting engine periodically polls the datasource, extracts metrics and process them.
So the backend plugin must receive this poll request, transform it to the custom API request, transform the custom API result to the Grafana-recognized
dataframe.

## Implementation
The code in this repo is the proof-of-concept.


Since Grafana backend plugins are running as separate processes and communicating via gRPC, they could be 
coded in any language with gRPC support. Or so they say ) So let's code it in Python.

The protobuf definitions are hosted at https://github.com/grafana/grafana-plugin-sdk-go/
so it should be the simple matter of compiling them for python and firing gRPC server.

The server handles just one gRPC request. 
Upon receiving QueryData it calls our custom API, receives data, transforms it and replies with QueryDataResponse.

## The plugin loading

Grafana loads the plugin executable and expects it will stdout the magic string with the versions and tcp port it listening at
i.e. ```1|2|tcp|127.0.0.1:50051|grpc```.
The python script should print this string upon startup. 
The plugin must be a single executable (pyinstaller to the rescue).

In order to keep the dev simple one could make a fake executable (fake.c -> fake.exe) to be launched by Grafana with the sole function of printing this
magic string. And launch the python code manually - gRPC server just listens to the socket after all.
