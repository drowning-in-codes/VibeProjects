package com.simplemusic;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@MapperScan(basePackages = {"com.simplemusic.mapper"})
@SpringBootApplication(scanBasePackages = "com.simplemusic")
public class SimpleMusicWebApplication {
    public static void main(String[] args) {
        SpringApplication.run(SimpleMusicWebApplication.class, args);
    }
}
