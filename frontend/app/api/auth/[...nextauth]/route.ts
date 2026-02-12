import NextAuth, { type NextAuthOptions } from "next-auth";
import GitHubProvider from "next-auth/providers/github";

const githubClientId = process.env.GITHUB_CLIENT_ID;
const githubClientSecret = process.env.GITHUB_CLIENT_SECRET;
const nextAuthUrl = process.env.NEXTAUTH_URL;

if (!githubClientId || !githubClientSecret) {
  console.error("[NextAuth] Missing GitHub env vars", {
    GITHUB_CLIENT_ID: githubClientId,
    has_GITHUB_CLIENT_SECRET: !!githubClientSecret,
  });
  // Fail fast so we never generate an authorization URL with an empty client_id.
  throw new Error(
    "Missing GitHub OAuth env vars. Check GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in .env.local."
  );
}

if (!nextAuthUrl) {
  console.warn(
    "[NextAuth] NEXTAUTH_URL is not set; GitHub callback URL should be http://localhost:3000/api/auth/callback/github in dev."
  );
}

const authOptions: NextAuthOptions = {
  debug: true,
  providers: [
    GitHubProvider({
      clientId: githubClientId,
      clientSecret: githubClientSecret,
      authorization: {
        params: {
          scope: "read:user",
        },
      },
    }),
  ],
  pages: {
    signIn: "/",
    error: "/",
  },
  callbacks: {
    async redirect({ url, baseUrl }) {
      // Allow relative URLs
      if (url.startsWith("/")) {
        return `${baseUrl}${url}`;
      }
      // Allow URLs from the same origin
      else if (new URL(url).origin === baseUrl) {
        return url;
      }
      // Default to dashboard on successful login
      return `${baseUrl}/dashboard`;
    },
  },
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };

// NOTE: After changing .env.local you MUST fully restart `npm run dev`
// so NextAuth picks up the new environment variables.

