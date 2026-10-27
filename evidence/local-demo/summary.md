# Nemotron concurrency smoke demo
Run status: complete

This finite workload uses a closed loop and a warmed image cache.
It does not establish overload behavior or production latency guarantees.
Tiny synthetic corpus: text sanity checks only, not a general OCR quality benchmark.
Latency starts at HTTP submission and ends after response validation.
It excludes preparation and waiting for a worker.
Raw per-request latencies and failed outputs are in results.json. Timeouts are censored observations.

| Concurrency | Inputs | Success | Failures | Timeouts | Elapsed s | Pages/s | All median s | All min–max s |
|---|---|---|---|---|---|---|---|---|
| 1 | 8 | 8 | 0 | 0 | 1.866 | 4.288 | 0.225 | 0.223–0.259 |
| 2 | 8 | 8 | 0 | 0 | 1.019 | 7.848 | 0.241 | 0.234–0.285 |
| 4 | 8 | 8 | 0 | 0 | 0.523 | 15.285 | 0.244 | 0.240–0.283 |
| 8 | 8 | 8 | 0 | 0 | 0.297 | 26.976 | 0.262 | 0.253–0.296 |

## Configuration and provenance

```json
{
  "started_at": "2026-10-27T02:36:30.043105+00:00",
  "python": "3.12.12",
  "platform": "Linux-7.2.0-ogc4.1.fc44.x86_64-x86_64-with-glibc2.43",
  "gpu_before": {
    "name": "NVIDIA GeForce RTX 4090",
    "uuid": "GPU-12cf2f75-8b19-004d-61af-9244dda7d725",
    "driver_version": "610.57.04",
    "memory.total": "24564",
    "memory.free": "12736",
    "utilization.gpu": "0"
  },
  "serving": {
    "model": "nvidia/Nemotron-3.5-Parse",
    "revision": "62cb1e4ba153d113ff64aaf2be6e068c377cf53c",
    "plugin": "3.5.0.post7",
    "vllm": "0.26.0",
    "image": "localhost/inference-lab-nemotron:0.1.0",
    "container": "inference-lab-nemotron",
    "port": 8017,
    "minimum_free_mib": 11000,
    "environment": {
      "NP_VLLM_MTP": "0"
    },
    "arguments": [
      "--model",
      "/model",
      "--served-model-name",
      "nemotron-parse",
      "--trust-remote-code",
      "--dtype",
      "bfloat16",
      "--distributed-executor-backend",
      "uni",
      "--tensor-parallel-size",
      "1",
      "--max-model-len",
      "16384",
      "--max-num-seqs",
      "8",
      "--max-num-batched-tokens",
      "16384",
      "--no-enable-prefix-caching",
      "--limit-mm-per-prompt",
      "{\"image\":1}",
      "--attention-config",
      "{\"flash_attn_version\":2}",
      "--gpu-memory-utilization",
      "0.4",
      "--enforce-eager",
      "--chat-template",
      "/model/chat_template.jinja",
      "--host",
      "0.0.0.0",
      "--port",
      "8000"
    ]
  },
  "container_id": "a28b38617469eac09ba8a402488d5ffa328126d960bf2c9e89f087d42e66f798",
  "image_id": "f261ace8dcf68c12f6c06ac4b5fa1d514df9303fd5f07ba200f50b175b16f01b",
  "container_args": [
    "-m",
    "vllm.entrypoints.openai.api_server",
    "--model",
    "/model",
    "--served-model-name",
    "nemotron-parse",
    "--trust-remote-code",
    "--dtype",
    "bfloat16",
    "--distributed-executor-backend",
    "uni",
    "--tensor-parallel-size",
    "1",
    "--max-model-len",
    "16384",
    "--max-num-seqs",
    "8",
    "--max-num-batched-tokens",
    "16384",
    "--no-enable-prefix-caching",
    "--limit-mm-per-prompt",
    "{\"image\":1}",
    "--attention-config",
    "{\"flash_attn_version\":2}",
    "--gpu-memory-utilization",
    "0.4",
    "--enforce-eager",
    "--chat-template",
    "/model/chat_template.jinja",
    "--host",
    "0.0.0.0",
    "--port",
    "8000"
  ],
  "packages": "accelerate==1.12.0\naiofile==3.11.1\naiofiles==25.1.0\naiohappyeyeballs==2.7.1\naiohttp==3.14.3\naiosignal==1.4.0\nannotated-doc==0.0.4\nannotated-types==0.8.0\nanthropic==0.120.0\nanyio==4.14.2\napache-tvm-ffi==0.1.10\nastor==0.8.1\nattrs==26.1.0\nawscrt==0.36.1\nazure-core==1.41.0\nazure-identity==1.25.3\nazure-storage-blob==12.30.0\nbeautifulsoup4==4.13.3\nbitsandbytes==0.50.0\nblake3==1.0.9\nblinker==1.4\nboto3==1.43.56\nbotocore==1.43.56\ncachetools==7.1.6\ncaio==0.9.25\ncbor2==6.1.3\ncertifi==2026.7.22\ncffi==2.1.0\ncharset-normalizer==3.4.9\nclick==8.4.2\ncloudpickle==3.1.2\ncompressed-tensors==0.17.0\ncryptography==49.0.0\ncuda-bindings==13.3.1\ncuda-core==1.0.1\ncuda-pathfinder==1.6.0\ncuda-python==13.3.1\ncuda-tile==1.5.0\ncuda-toolkit==13.0.2\ncufile-python==0.2.0\ncupy-cuda13x==14.0.1\ndbus-python==1.2.18\ndeep_ep @ file:///vllm-workspace/ep_kernels/dist/deep_ep-1.2.1+73b6ea4-cp312-cp312-linux_x86_64.whl\ndepyf==0.20.0\ndetect-installer==0.1.0\ndill==0.4.1\ndistro==1.9.0\ndnspython==2.8.0\ndocstring_parser==0.18.0\neinops==0.8.1\nemail-validator==2.3.0\nfastapi==0.136.3\nfastapi-cli==0.0.32\nfastapi-cloud-cli==0.22.2\nfastar==0.11.0\nfastsafetensors==0.3.3\nfilelock==3.32.0\nflashinfer-cubin==0.6.14\nflashinfer-jit-cache==0.6.14+cu130\nflashinfer-python==0.6.14\nfrozenlist==1.8.0\nfsspec==2026.6.0\ngoogle-api-core==2.33.0\ngoogle-auth==2.56.2\ngoogle-cloud-bigtable==2.41.0\ngoogle-cloud-core==2.6.0\ngoogle-cloud-storage==3.13.0\ngoogle-crc32c==1.8.0\ngoogle-resumable-media==2.10.0\ngoogleapis-common-protos==1.75.0\ngrpc-google-iam-v1==0.14.4\ngrpcio==1.83.0\ngrpcio-status==1.83.0\nh11==0.16.0\nhf-xet==1.5.2\nhttpcore==1.0.9\nhttplib2==0.20.2\nhttptools==0.8.0\nhttpx==0.28.1\nhttpx-sse==0.4.3\nhuggingface_hub==1.24.0\nhumanize==4.16.0\nhumming-kernels==0.1.10\nidna==3.18\nijson==3.5.1\nimportlib_metadata==8.7.1\niniconfig==2.3.0\ninteregular==0.3.3\nisodate==0.7.2\njeepney==0.7.1\nJinja2==3.1.6\njiter==0.16.0\njmespath==1.1.0\njsonschema==4.26.0\njsonschema-specifications==2025.9.1\nkeyring==23.5.0\nlark==1.2.2\nlaunchpadlib==1.10.16\nlazr.restfulclient==0.14.4\nlazr.uri==1.0.6\nllguidance==1.7.6\nllvmlite==0.47.0\nlm-format-enforcer==0.11.3\nlmcache==0.5.2\nloguru==0.7.3\nmarkdown-it-py==4.2.0\nMarkupSafe==3.0.3\nmcp==1.28.1\nmdurl==0.1.2\nmistral_common==1.11.7\nml_dtypes==0.5.4\nmodel-hosting-container-standards==0.1.16\nmodelscope==1.37.1\nmooncake-transfer-engine @ https://vllm-wheels.s3.amazonaws.com/mooncake/mooncake_transfer_engine-0.3.10.post2-0da9dfea3-cp312-cp312-manylinux_2_35_x86_64.whl\nmore-itertools==8.10.0\nmpmath==1.3.0\nmsal==1.37.0\nmsal-extensions==1.3.1\nmsgpack==1.2.1\nmsgspec==0.21.1\nmultidict==6.7.1\nnemotron-parse @ file:///model\nnetworkx==3.6.1\nninja==1.13.0\nnixl-cu12==1.3.1\nnixl-cu13==1.3.2\nnumba==0.65.0\nnumpy==2.2.6\nnvidia-cublas==13.1.0.3\nnvidia-cuda-cccl==13.3.3.4.1\nnvidia-cuda-crt==13.3.73\nnvidia-cuda-cupti==13.0.85\nnvidia-cuda-nvcc==13.3.73\nnvidia-cuda-nvdisasm==13.3.73\nnvidia-cuda-nvrtc==13.0.88\nnvidia-cuda-runtime==13.0.96\nnvidia-cudnn-cu13==9.19.0.56\nnvidia-cudnn-frontend==1.26.0\nnvidia-cufft==12.0.0.61\nnvidia-cufile==1.15.1.6\nnvidia-curand==10.4.0.35\nnvidia-cusolver==12.0.4.66\nnvidia-cusparse==12.6.3.3\nnvidia-cusparselt-cu13==0.8.0\nnvidia-cutlass-dsl==4.6.0\nnvidia-cutlass-dsl-libs-base==4.6.0\nnvidia-cutlass-dsl-libs-core==4.6.0\nnvidia-cutlass-dsl-libs-cu12==4.6.0\nnvidia-cutlass-dsl-libs-cu13==4.6.0\nnvidia-ml-py==13.610.43\nnvidia-nccl-cu13==2.28.9\nnvidia-nvjitlink==13.0.88\nnvidia-nvshmem-cu13==3.4.5\nnvidia-nvtx==13.0.85\nnvidia-nvvm==13.3.73\nnvtx==0.2.15\noauthlib==3.2.0\nopenai==2.30.0\nopenai-harmony==0.0.8\nopencv-python-headless==5.0.0.93\nopentelemetry-api==1.40.0\nopentelemetry-exporter-otlp==1.40.0\nopentelemetry-exporter-otlp-proto-common==1.40.0\nopentelemetry-exporter-otlp-proto-grpc==1.40.0\nopentelemetry-exporter-otlp-proto-http==1.40.0\nopentelemetry-exporter-prometheus==0.61b0\nopentelemetry-proto==1.40.0\nopentelemetry-sdk==1.40.0\nopentelemetry-semantic-conventions==0.61b0\nopentelemetry-semantic-conventions-ai==0.5.1\noutlines_core==0.2.14\npackaging==26.2\npartial-json-parser==0.2.1.1.post7\npillow==12.3.0\npluggy==1.6.0\nprometheus-fastapi-instrumentator==8.0.2\nprometheus_client==0.24.1\npropcache==0.5.2\nproto-plus==1.28.2\nprotobuf==6.33.6\npsutil==7.2.2\npy-cpuinfo==9.0.0\npyasn1==0.6.4\npyasn1_modules==0.4.2\npybase64==1.4.3\npycairo==1.20.1\npycountry==26.2.16\npycparser==3.0\npydantic==2.13.4\npydantic-extra-types==2.11.1\npydantic-settings==2.14.2\npydantic_core==2.46.4\npyelftools==0.33\nPygments==2.20.0\nPyGObject==3.42.1\nPyJWT==2.13.0\npynvvideocodec==2.0.4\npyparsing==2.4.7\npytest==9.1.1\npython-apt==2.4.0+ubuntu4.1\npython-dateutil==2.9.0.post0\npython-dotenv==1.2.2\npython-json-logger==4.1.0\npython-multipart==0.0.32\nPyYAML==6.0.3\npyzmq==27.1.0\nquack-kernels==0.6.1\nredis==8.0.1\nreferencing==0.37.0\nregex==2026.7.19\nrequests==2.34.2\nrich==15.0.0\nrich-toolkit==0.20.3\nrignore==0.8.0\nrpds-py==2026.6.3\nrunai-model-streamer==0.16.1\nrunai-model-streamer-azure==0.16.1\nrunai-model-streamer-gcs==0.16.1\nrunai-model-streamer-s3==0.16.1\ns3transfer==0.19.2\nsafetensors==0.8.0\nSecretStorage==3.3.1\nsentencepiece==0.2.2\nsentry-sdk==2.66.1\nsetproctitle==1.3.7\nsetuptools==80.10.2\nsetuptools-scm==10.2.1\nshellingham==1.5.4\nsix==1.17.0\nsniffio==1.3.1\nsortedcontainers==2.4.0\nsoupsieve==3.0.4\nsse-starlette==3.4.6\nstarlette==1.3.1\nsupervisor==4.3.0\nsympy==1.14.0\ntabulate==0.10.0\ntiktoken==0.13.0\ntilelang==0.1.9\ntimm==1.0.22\ntokenizers==0.22.2\ntokenspeed-mla==0.1.8\ntokenspeed-triton==3.8.10.post20260721\ntorch==2.11.0+cu130\ntorch_c_dlpack_ext==0.1.5\ntorchaudio==2.11.0+cu130\ntorchcodec==0.15.0+cu130\ntorchvision==0.26.0+cu130\ntqdm==4.69.1\ntransformers==5.14.1\ntriton==3.6.0\ntyper==0.27.0\ntyping-inspection==0.4.2\ntyping_extensions==4.16.0\nurllib3==2.7.0\nuv==0.11.32\nuvicorn==0.51.0\nuvloop==0.22.1\nvcs-versioning==2.2.2\nvllm @ file:///vllm-workspace/dist/vllm-0.26.0-cp38-abi3-linux_x86_64.whl\nwadllib==1.3.6\nwatchfiles==1.2.0\nwebsockets==16.1.1\nxgrammar==0.2.3\nyarl==1.24.5\nz3-solver==4.15.4.0\nzipp==4.1.0",
  "git_commit": "b3df45155609747b9191bcc25df5699a6438d29f",
  "git_dirty": true,
  "client_url": "http://127.0.0.1:8017",
  "timeout_s": 120.0,
  "preparation_s": 0.09030012402217835,
  "warmup_policy": "one serial request per corpus page before measurement",
  "cache_policy": "prefix cache disabled; default multimodal cache retained and warmed",
  "quality": "all expected phrases after case/punctuation normalization",
  "corpus": [
    {
      "file": "page-01.png",
      "sha256": "0ca3464c0e472c49b951d61bf5dc170d4c9262babc33085b32e28dc06516d6dc",
      "expected": [
        "INFERENCE LAB PAGE 1",
        "Synthetic inventory record",
        "Item: cobalt notebook 1",
        "Quantity: 12",
        "Reference: LAB401",
        "All entries are fictional."
      ]
    },
    {
      "file": "page-02.png",
      "sha256": "01f0733db59a15c1f688124c6b980f22d3686e6e0b4686ae84298d6e2a27fc40",
      "expected": [
        "INFERENCE LAB PAGE 2",
        "Synthetic inventory record",
        "Item: cobalt notebook 2",
        "Quantity: 13",
        "Reference: LAB402",
        "All entries are fictional."
      ]
    },
    {
      "file": "page-03.png",
      "sha256": "d6ecfd7bdc9ddc115c9feeda17c875892c9f80eef219d459245b9c5b03759a00",
      "expected": [
        "INFERENCE LAB PAGE 3",
        "Synthetic inventory record",
        "Item: cobalt notebook 3",
        "Quantity: 14",
        "Reference: LAB403",
        "All entries are fictional."
      ]
    },
    {
      "file": "page-04.png",
      "sha256": "ed589d7783ddf05dc1ed4f30cb84542cf581f08ffa9ad4793655797f935230e9",
      "expected": [
        "INFERENCE LAB PAGE 4",
        "Synthetic inventory record",
        "Item: cobalt notebook 4",
        "Quantity: 15",
        "Reference: LAB404",
        "All entries are fictional."
      ]
    },
    {
      "file": "page-05.png",
      "sha256": "034491dde5a45eff99ca3c8a5ecf2b56e557c0505b996ac6040d19d1a8cfd234",
      "expected": [
        "INFERENCE LAB PAGE 5",
        "Synthetic inventory record",
        "Item: cobalt notebook 5",
        "Quantity: 16",
        "Reference: LAB405",
        "All entries are fictional."
      ]
    },
    {
      "file": "page-06.png",
      "sha256": "9426d1e29edcdc4f2d0d65b8478c95f26b766e89b80621edbd799a8fe31a2f53",
      "expected": [
        "INFERENCE LAB PAGE 6",
        "Synthetic inventory record",
        "Item: cobalt notebook 6",
        "Quantity: 17",
        "Reference: LAB406",
        "All entries are fictional."
      ]
    },
    {
      "file": "page-07.png",
      "sha256": "3f23a473536676ffefda49a10efdcfe9c613477d100d6de0eac46f2eaa8380e5",
      "expected": [
        "INFERENCE LAB PAGE 7",
        "Synthetic inventory record",
        "Item: cobalt notebook 7",
        "Quantity: 18",
        "Reference: LAB407",
        "All entries are fictional."
      ]
    },
    {
      "file": "page-08.png",
      "sha256": "73d6bae5ead72c94510cec0d91bfe56082b5e210e0115b4ea461695b38db5f5e",
      "expected": [
        "INFERENCE LAB PAGE 8",
        "Synthetic inventory record",
        "Item: cobalt notebook 8",
        "Quantity: 19",
        "Reference: LAB408",
        "All entries are fictional."
      ]
    }
  ],
  "finished_at": "2026-10-27T02:36:37.444791+00:00"
}
```
