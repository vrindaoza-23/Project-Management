## What & why

Describe the change and the motivation.

## How I verified

- [ ] Backend tests pass (`bench run-tests --app projex --skip-before-tests`)
- [ ] Frontend builds (`cd frontend && yarn build`)
- [ ] Manually checked the affected screen(s)

## Checklist

- [ ] No hardcoded domain data in the frontend (data comes from the API)
- [ ] Server-side permissions respected
- [ ] Stays within the v1 scope ceiling
- [ ] No secrets committed
- [ ] Conventional commit messages
