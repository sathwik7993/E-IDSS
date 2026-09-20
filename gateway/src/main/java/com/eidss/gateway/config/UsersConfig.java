package com.eidss.gateway.config;

import com.eidss.gateway.security.Role;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;

/**
 * Seeds the three demo users this hackathon build ships with. Real deployments would swap
 * this for a proper identity provider / directory-backed UserDetailsService; for the demo we
 * want the credentials to be obvious, so they're logged on boot below.
 */
@Configuration
public class UsersConfig {

    private static final Logger log = LoggerFactory.getLogger(UsersConfig.class);

    private record DemoUser(String username, String password, Role role) {
    }

    private static final DemoUser[] DEMO_USERS = {
            new DemoUser("operator", "operator123", Role.OPERATOR),
            new DemoUser("linelead", "linelead123", Role.LINE_LEAD),
            new DemoUser("manager", "manager123", Role.PLANT_MANAGER),
    };

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public UserDetailsService userDetailsService(PasswordEncoder passwordEncoder) {
        InMemoryUserDetailsManager manager = new InMemoryUserDetailsManager();
        for (DemoUser demoUser : DEMO_USERS) {
            manager.createUser(User.withUsername(demoUser.username())
                    .password(passwordEncoder.encode(demoUser.password()))
                    .authorities(demoUser.role().authority())
                    .build());
        }
        return manager;
    }

    /**
     * Prints the demo credentials on startup so they're discoverable for a live demo without
     * digging through source. This is intentionally loud and intentionally insecure — it is a
     * hackathon seed, not a production credential store.
     */
    @Bean
    public CommandLineRunner logDemoCredentials() {
        return args -> {
            log.info("==================================================================");
            log.info(" E-IDSS Governance Gateway - demo credentials (seeded in-memory)");
            log.info("------------------------------------------------------------------");
            for (DemoUser demoUser : DEMO_USERS) {
                log.info(" {} / {}  -> role {}", demoUser.username(), demoUser.password(), demoUser.role());
            }
            log.info("==================================================================");
        };
    }
}
