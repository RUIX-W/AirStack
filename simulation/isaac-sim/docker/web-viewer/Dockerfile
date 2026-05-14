FROM nvcr.io/nvidia/base/ubuntu:noble-20251013 AS builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git \
    && curl -fsSL --proto '=https' https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN echo '@nvidia:registry=https://edge.urm.nvidia.com/artifactory/api/npm/omniverse-client-npm/' >> /root/.npmrc \
    && npx @nvidia/create-ov-web-rtc-app@1.14.2 --name web-viewer --sample local-sample --outputDir /app \
    && rm -f /root/.npmrc

WORKDIR /app/web-viewer

ARG ISAAC_SIM_WEBRTC_SIGNAL_PORT=49100
ARG ISAAC_SIM_WEBRTC_STREAM_PORT=47998

RUN sed -i "s/signalingServer: [^,]*/signalingServer: window.location.hostname/" src/main.ts \
    && sed -i "/signalingServer:/a\\  signalingPort: ${ISAAC_SIM_WEBRTC_SIGNAL_PORT},\\n  mediaServer: window.location.hostname,\\n  mediaPort: ${ISAAC_SIM_WEBRTC_STREAM_PORT},\\n  forceWSS: false," src/main.ts

RUN npm install --ignore-scripts \
    && npm run build

FROM nvcr.io/nvidia/base/ubuntu:noble-20251013

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl -fsSL --proto '=https' https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser --gid 1234 \
    && useradd --no-log-init -r -g appuser --uid 1234 -d /app -s /usr/sbin/nologin appuser

WORKDIR /app

COPY --from=builder --chmod=755 /app/web-viewer/package.json ./

RUN echo '@nvidia:registry=https://edge.urm.nvidia.com/artifactory/api/npm/omniverse-client-npm/' >> /root/.npmrc \
    && npm install --ignore-scripts \
    && npm cache clean --force \
    && rm -f /root/.npmrc \
    && chown -R appuser:appuser /app

COPY --from=builder --chmod=755 /app/web-viewer/dist ./dist

USER appuser

EXPOSE 8210

CMD ["npx", "vite", "preview", "--host", "0.0.0.0", "--port", "8210"]
