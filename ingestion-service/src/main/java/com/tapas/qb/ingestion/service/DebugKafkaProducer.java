package com.tapas.qb.ingestion.service;

import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Service
public class DebugKafkaProducer {

    private final KafkaTemplate<Object, Object> template;

    public DebugKafkaProducer(KafkaTemplate<Object, Object> template) {
        this.template = template;
    }

    public void sendTest(String msg) {
        template.send("order-created-events", msg).whenComplete((result, ex) -> {
            if (ex != null) {
                ex.printStackTrace();
            } else {
                System.out.println("Sent to topic " + result.getRecordMetadata().topic()
                        + " partition " + result.getRecordMetadata().partition()
                        + " offset " + result.getRecordMetadata().offset());
            }
        });
    }
}
