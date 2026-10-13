package de.jumpstone.plugins.proxy.velocity;

import com.google.inject.Inject;
import com.velocitypowered.api.plugin.Plugin;
import com.velocitypowered.api.proxy.ProxyServer;
import org.slf4j.Logger;
import com.velocitypowered.api.event.Subscribe;
import com.velocitypowered.api.event.proxy.ProxyInitializeEvent;
import com.velocitypowered.api.proxy.messages.MinecraftChannelIdentifier;

@Plugin(id = "hmt-sync", name = "HMT Sync", version = "1.0.3", authors = {
        "jumpstone" })
public class VelocityHMTSync {

    private final ProxyServer server;
    private final Logger logger;
    private final MinecraftChannelIdentifier channel = MinecraftChannelIdentifier.create("hmt-sync", "main");

    @Inject
    public VelocityHMTSync(ProxyServer server, Logger logger) {
        this.server = server;
        this.logger = logger;
    }

    @Subscribe
    public void onProxyInitialization(ProxyInitializeEvent event) {
        server.getChannelRegistrar().register(channel);
        server.getEventManager().register(this, new VelocityListener(this));
        
        com.velocitypowered.api.command.CommandMeta meta = server.getCommandManager().metaBuilder("hmtsync")
                .aliases("db")
                .build();
        server.getCommandManager().register(meta, new VelocityUnlockCommand(this));
        
        logger.info("hmt-sync has been enabled on Velocity!");
    }

    public ProxyServer getServer() {
        return server;
    }

    public MinecraftChannelIdentifier getChannel() {
        return channel;
    }

    public Logger getLogger() {
        return logger;
    }
}
