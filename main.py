import requests
import logging
import json
from concurrent import futures

import pyarrow as pa

import grpc

import backend_pb2_grpc as backend_grpc
import backend_pb2 as backend

# local port our plugin is listening at
PORT = 50051


# this is data fetcher requesting data from our http api.
# the response json is:
# [
#   {
#       name: field a name,
#       values: [array of a samples]
#       meta: { field a meta info}
#   },
#   {
#       name: field b name,
#       values: [array of b samples]
#       meta: { field a meta info}
#   },
#   ...
# ]
#
# the fields to be fetched and time range are specified in url as parameters
#
def fetch_data(ds, targ, from_, to):
    fields = targ['fields']
    # time field is a must
    if '_time' not in fields:
        fields = ['_time'] + fields[:]

    url = 'http://{url}/api/things/{thing}/db/{table}/frames'.format(
        url=ds['url'],
        thing=ds['thing'],
        table=targ['table']
    )

    params = {
        'from':from_,
        'to':to,
        'fields':fields,
        'indexes':targ['indexes'],
        'meta':True
    }
    r = requests.get(url, params=params)
    frames = r.json()
    return frames

# this function encodes our api response to the arrow format expected by grafana.
#
# the _time field is special, it should be converted to arrow nanosecond timestamp type.
# grafana seems to look for the field with the timestamp type
# in order to recognize the table as timeseries
#
# other fields encoded as arrays of float64's.
# the grafana-recognized displayNameFromDS property of field is set to the custom
# text to better describe the metric. the custom text is generated from metadata returned by api
#
# refId of request is embedded into the frame to link request and response
#
# the arrow table is serialized to file and bytes representaion is returned
def to_arrow(frames, name, refid):
    fields = []
    data = []

    for f in frames:
        fname = f['name']
        if fname == '_time':
            field = pa.field(fname, pa.timestamp('ns'))
            fields.append(field)
            data.append([v * 1000000000 for v in f['values']])
        else:
            our_meta = f['meta']
            displayname = ': '.join([our_meta['group_txt'], our_meta['txt']])
            config = json.dumps({'displayNameFromDS': displayname})
            metadata = {'name':fname, 'config':config}
            #
            field = pa.field(fname, pa.float64(), metadata=metadata)
            fields.append(field)
            data.append(f['values'])

    schema = pa.schema(fields, metadata={'refId':refid})
    table = pa.table(data, schema=schema)

    sink = pa.BufferOutputStream()
    writer = pa.ipc.new_file(sink, schema)
    writer.write(table)
    writer.close()
    return sink.getvalue().to_pybytes()

# plugin implementation class
# only QueryData method is implemented
class Plug():
    def QueryData(self, request, context):
        print(request)
        # protobuf response to be composed
        resp = backend.QueryDataResponse()

        # extract our specific config from general data source settings
        ds = request.pluginContext.dataSourceInstanceSettings
        ds_cfg = json.loads(ds.jsonData)

        # request is a list of queries.
        # each query may have specific settings
        for q in request.queries:
            print(q)
            # query our api with the setting specific to our query model (fields, indexes etc).
            # NOTE: our api timestamps have a second precision while grafana timestamps are in ms
            targ = json.loads(q.json)
            data = fetch_data(
                ds_cfg,
                targ,
                q.timeRange.fromEpochMS // 1000,
                q.timeRange.toEpochMS // 1000,
            )

            ar = to_arrow(data, '', q.refId)
            # WTF: why the frames are 'repeated' in proto ?
            resp.responses[q.refId].frames.append(ar)

        return resp

def main():
    logging.basicConfig()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))

    plug = Plug()
    backend_grpc.add_DataServicer_to_server(plug, server)

    #backend_grpc.add_DiagnosticsServicer_to_server(plug, server)
    #backend_grpc.add_ResourceServicer_to_server(plug, server)

    # this is the hashicorp stuff. seems to be not required
    #health = HealthServicer()
    #health.set("plugin", health_pb2.HealthCheckResponse.ServingStatus.Value('SERVING'))
    #health_pb2_grpc.add_HealthServicer_to_server(health, server)

    server.add_insecure_port('127.0.0.1:%d' % PORT)
    server.start()
    server.wait_for_termination()

main()
