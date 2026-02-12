/**
 * Pera Wallet (Algorand) integration.
 * Connect wallet, sign txns, link to backend user.
 */

import type { PeraWalletConnect } from "@perawallet/connect";

let peraWallet: PeraWalletConnect | null = null;

/**
 * Lazy-load Pera Wallet (client-side only)
 */
async function getPeraWallet(): Promise<PeraWalletConnect> {
  if (typeof window === "undefined") {
    throw new Error("Pera Wallet is only available in the browser");
  }

  if (!peraWallet) {
    const module = await import("@perawallet/connect");
    const PeraWalletConnect = module.PeraWalletConnect;

    peraWallet = new PeraWalletConnect({
      chainId: 416002, // Algorand TestNet
    });
  }

  return peraWallet;
}

/**
 * Connect wallet
 */
export async function connectPeraWallet(): Promise<string[]> {
  const wallet = await getPeraWallet();
  const accounts = await wallet.connect();
  return accounts;
}

/**
 * Disconnect wallet
 */
export async function disconnectPeraWallet(): Promise<void> {
  const wallet = await getPeraWallet();
  await wallet.disconnect();
}

/**
 * Get currently connected accounts
 */
export async function getConnectedAccounts(): Promise<string[]> {
  const wallet = await getPeraWallet();
  return wallet.connector?.accounts ?? [];
}

/**
 * Listen for wallet connect event
 */
export async function onPeraWalletConnect(
  cb: (accounts: string[]) => void
): Promise<() => void> {
  const wallet = await getPeraWallet();

  const handler = (accounts: { address: string }[]) => {
    cb(accounts.map((a) => a.address));
  };

  wallet.connector?.on("connect", handler);

  return () => {
    wallet.connector?.off?.("connect", handler);
  };
}
