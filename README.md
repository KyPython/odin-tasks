# Harbor workspace

A small pnpm/Turborepo workspace used to exercise service build reliability.

## Setup

```sh
corepack pnpm install --frozen-lockfile
```

## Reproduce the service build

```sh
corepack pnpm build:service
```

Run the independent workspace check with:

```sh
corepack pnpm check:unrelated
```

The container target can be checked separately with:

```sh
corepack pnpm check:container
```
