# --- Build stage ---
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /build

# Cache dependencies separately from source for faster rebuilds.
COPY pom.xml .
RUN mvn -q -B dependency:go-offline || true

COPY src ./src
RUN mvn -q -B -DskipTests package

# --- Runtime stage ---
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

# Non-root runtime user.
RUN addgroup -S eidss && adduser -S eidss -G eidss
COPY --from=build /build/target/gateway.jar /app/gateway.jar
USER eidss

EXPOSE 8080

# No FastAPI dependency at startup: proxy calls simply return 502 (Bad Gateway) with a JSON
# body until the backend at eidss.backend.url / BACKEND_URL is reachable.
ENTRYPOINT ["java", "-jar", "/app/gateway.jar"]
