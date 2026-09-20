import json
from pathlib import Path
import tempfile
import unittest
from skill_erosion.embeddings.chroma import ChromaStore

class SharedStoreSafetyTests(unittest.TestCase):
    def test_unavailable_shared_service_never_falls_back_to_embedded_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'chroma'
            (path.parent/'chroma-server.json').write_text(json.dumps({'path':str(path.resolve()),'port':1,'pid':0}))
            client=None
            try:
                with self.assertRaisesRegex(RuntimeError,'shared Chroma'):
                    client=ChromaStore(path)
            finally:
                if client is not None:
                    client.client.close()

    def test_long_lived_reader_sees_new_attempts_from_another_process(self):
        import socket
        import subprocess
        import sys
        from skill_erosion.embeddings.service import start_chroma, stop_chroma
        from skill_erosion.contracts.models import Attempt
        from tests.unit.helpers import record
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"chroma"
            with socket.socket() as sock:
                sock.bind(("127.0.0.1",0))
                port=sock.getsockname()[1]
            with (Path(directory)/"server.log").open("w",encoding="utf-8") as log:
                service=start_chroma(path,port,log)
                reader=None
                try:
                    reader=ChromaStore(path)
                    reader.upsert_attempts([Attempt(**record(1))])
                    reader.similar_attempts("loop range boundary","s1","python.loops")
                    writer="from skill_erosion.embeddings.chroma import ChromaStore; from skill_erosion.contracts.models import Attempt; from tests.unit.helpers import record; import sys; s=ChromaStore(sys.argv[1]); s.upsert_attempts([Attempt(**record(i)) for i in (3,5,7)]); s.client.close()"
                    completed=subprocess.run([sys.executable,"-c",writer,str(path)],capture_output=True,text=True,timeout=45)
                    self.assertEqual(completed.returncode,0,completed.stderr)
                    found=reader.similar_attempts("loop range boundary","s1","python.loops")
                    self.assertEqual({item[0] for item in found},{"a1@v1","a3@v1","a5@v1","a7@v1"})
                    self.assertEqual(reader.counts()["skill-erosion-attempts"],4)
                finally:
                    if reader is not None:
                        reader.client.close()
                    stop_chroma(service,path)
            self.assertFalse((path.parent/"chroma-server.json").exists())

    def test_stale_descriptor_cannot_connect_to_another_dataset_on_reused_port(self):
        import socket
        from skill_erosion.embeddings.service import start_chroma, stop_chroma
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            first_path=root/"first/chroma"
            second_path=root/"second/chroma"
            with socket.socket() as sock:
                sock.bind(("127.0.0.1",0))
                port=sock.getsockname()[1]
            with (root/"server.log").open("w",encoding="utf-8") as log:
                first=start_chroma(first_path,port,log)
                stale=(first_path.parent/"chroma-server.json").read_text(encoding="utf-8")
                stop_chroma(first,first_path)
                (first_path.parent/"chroma-server.json").write_text(stale,encoding="utf-8")
                second=start_chroma(second_path,port,log)
                try:
                    with self.assertRaisesRegex(RuntimeError,"shared Chroma"):
                        ChromaStore(first_path)
                finally:
                    stop_chroma(second,second_path)
