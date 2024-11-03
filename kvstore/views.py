from django.utils import timezone
from rest_framework import viewsets
from rest_framework.response import Response
from .models import KeyValue
from .serializers import KeyValueSerializer
import random


class KeyValueViewSet(viewsets.ViewSet):
    def list(self, request):
        queryset = KeyValue.objects.all()
        serializer = KeyValueSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = KeyValueSerializer(data=request.data)
        if serializer.is_valid():
            key = serializer.validated_data['key']
            value = serializer.validated_data['value']
            if distributed_store.write(key, {'value': value, 'timestamp': timezone.now()}):
                serializer.save()
                return Response(serializer.data, status=201)
            else:
                return Response({"error": "Failed to achieve write quorum"}, status=500)
        return Response(serializer.errors, status=400)

    def retrieve(self, request, pk=None):
        result = distributed_store.read(pk)
        if result:
            return Response({"key": pk, "value": result['value'], "timestamp": result['timestamp']})
        return Response(status=404)

    def update(self, request, pk=None):
        serializer = KeyValueSerializer(data=request.data)
        if serializer.is_valid():
            value = serializer.validated_data['value']
            if distributed_store.write(pk, {'value': value, 'timestamp': timezone.now()}):
                try:
                    kv = KeyValue.objects.get(key=pk)
                    kv.value = value
                    kv.save()
                except KeyValue.DoesNotExist:
                    KeyValue.objects.create(key=pk, value=value)
                return Response(serializer.data)
            else:
                return Response({"error": "Failed to achieve write quorum"}, status=500)
        return Response(serializer.errors, status=400)

    def destroy(self, request, pk=None):
        if distributed_store.delete(pk):
            try:
                kv = KeyValue.objects.get(key=pk)
                kv.delete()
            except KeyValue.DoesNotExist:
                pass
            return Response(status=204)
        return Response({"error": "Failed to achieve delete quorum"}, status=500)


class Node:
    def __init__(self, id):
        self.id = id
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

    def delete(self, key):
        if key in self.data:
            del self.data[key]


class DistributedKeyValueStore:
    def __init__(self, node_count=3):
        self.nodes = [Node(i) for i in range(node_count)]

    def get_quorum_size(self):
        return (len(self.nodes) // 2) + 1

    def read(self, key):
        quorum_size = self.get_quorum_size()
        responses = []
        for node in random.sample(self.nodes, quorum_size):
            value = node.get(key)
            if value is not None:
                responses.append(value)
        return max(responses, key=lambda x: x['timestamp']) if responses else None

    def write(self, key, value):
        quorum_size = self.get_quorum_size()
        successful_writes = 0
        for node in self.nodes:
            node.set(key, value)
            successful_writes += 1
            if successful_writes >= quorum_size:
                return True
        return False

    def delete(self, key):
        quorum_size = self.get_quorum_size()
        successful_deletes = 0
        for node in self.nodes:
            node.delete(key)
            successful_deletes += 1
            if successful_deletes >= quorum_size:
                return True
        return False


distributed_store = DistributedKeyValueStore()
