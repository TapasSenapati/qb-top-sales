FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

# Copy the built jar into the image
COPY target/ingestion-service-*.jar app.jar

EXPOSE 8081

ENTRYPOINT ["java", "-jar", "app.jar"]
