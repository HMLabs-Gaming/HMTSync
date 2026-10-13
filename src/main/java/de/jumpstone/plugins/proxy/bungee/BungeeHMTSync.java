package de.jumpstone.plugins.proxy.bungee;

import net.md_5.bungee.api.plugin.Plugin;

public class BungeeHMTSync extends Plugin {

    @Override
    public void onEnable() {
        getLogger().info("hmt-sync has been enabled on BungeeCord!");
        getProxy().registerChannel("hmt-sync:main");
        getProxy().getPluginManager().registerListener(this, new BungeeListener(this));
        getProxy().getPluginManager().registerCommand(this, new BungeeUnlockCommand(this));
    }
}
