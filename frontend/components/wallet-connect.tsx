"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { linkWallet, getMe } from "@/lib/api";
import {
  connectPeraWallet,
  disconnectPeraWallet,
  getConnectedAccounts,
} from "@/wallet/pera";

export function WalletConnect() {
  const [address, setAddress] = useState<string | null>(null);
  const [linking, setLinking] = useState(false);

  useEffect(() => {
    getConnectedAccounts().then((accounts) => {
      if (accounts.length) setAddress(accounts[0]);
    });
  }, []);

  const handleConnect = async () => {
    try {
      const accounts = await connectPeraWallet();
      if (accounts.length) setAddress(accounts[0]);
    } catch (e) {
      console.error(e);
    }
  };

  const handleDisconnect = async () => {
    await disconnectPeraWallet();
    setAddress(null);
  };

  const handleLinkToAccount = async () => {
    if (!address) return;
    setLinking(true);
    try {
      await linkWallet(address);
      window.location.reload();
    } catch (e) {
      console.error(e);
    } finally {
      setLinking(false);
    }
  };

  if (address) {
    return (
      <div className="flex items-center gap-2">
        <span className="max-w-[120px] truncate text-sm text-muted-foreground">
          {address.slice(0, 6)}...{address.slice(-4)}
        </span>
        <Button variant="outline" size="sm" onClick={handleLinkToAccount} disabled={linking}>
          {linking ? "Linking..." : "Link to account"}
        </Button>
        <Button variant="ghost" size="sm" onClick={handleDisconnect}>
          Disconnect
        </Button>
      </div>
    );
  }

  return (
    <Button variant="outline" size="sm" onClick={handleConnect}>
      Connect Pera Wallet
    </Button>
  );
}
