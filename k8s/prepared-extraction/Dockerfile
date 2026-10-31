# The qualified, cleaned environment: Python, native libraries, browser and fonts.
# Keep this immutable base available; building this file does not activate a worker.
FROM faisalanjum/report-enricher@sha256:23ca15adc2b1f265ec862a1af2bfa471cc525a6b18b25524049b044803c6236b

# Native Chandra client only; GPU inference stays on the separately pinned server.
COPY k8s/prepared-extraction/requirements-ocr.txt /opt/prepared/requirements-ocr.txt
RUN /opt/prepared/venv/bin/python -m pip install --no-cache-dir --no-deps --require-hashes \
    -r /opt/prepared/requirements-ocr.txt

# The qualified base already contains these unchanged native CPU reader factories.
# Populate their native caches at build time, then verify the complete weight hashes.
ENV ONNXTR_CACHE_DIR=/opt/prepared/ocr-cache
COPY k8s/prepared-extraction/cpu-models.sha256 /opt/prepared/cpu-models.sha256
RUN cd /opt/prepared/runtime \
 && /opt/prepared/venv/bin/python -B -c "from driver.prepare.pictures.readers import _free_tools; _free_tools()" \
 && sha256sum -c /opt/prepared/cpu-models.sha256

# Use the active application and its existing package metadata.
RUN rm -rf /app/src/eventtrader /app/venv/src/eventtrader \
 && sed -i 's|^/app/src/eventtrader$|/app|' \
    /usr/local/lib/python3.11/site-packages/easy-install.pth \
    /usr/local/lib/python3.11/site-packages/eventtrader.egg-link

COPY driver/__init__.py driver/README.md /opt/prepared/runtime/driver/
COPY driver/prepare/ /opt/prepared/runtime/driver/prepare/
COPY driver/reference_data/ /opt/prepared/runtime/driver/reference_data/
COPY k8s/prepared-extraction/RUNTIME_MANIFEST.json /opt/prepared/runtime/RUNTIME_MANIFEST_ROLE.json
COPY redisDB/prepared_filing.py /opt/prepared/adapter/prepared_filing.py
COPY redisDB/report_enricher.py redisDB/redisClasses.py /app/redisDB/
RUN chmod -R a-w /opt/prepared/runtime /opt/prepared/adapter
