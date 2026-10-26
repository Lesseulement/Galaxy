-- Все сессии в Redis: ключ, пользователь сессии и сколько секунд ей осталось жить.
-- Запуск: docker exec -it galaxy_redis redis-cli --eval /scripts/sessions.lua
local result = {}
local keys = redis.call('KEYS', 'session:*')
for _, key in ipairs(keys) do
  local session = cjson.decode(redis.call('GET', key))
  table.insert(result, key)
  table.insert(result, 'user_id = ' .. session.user_id .. ', username = ' .. session.username)
  table.insert(result, 'TTL = ' .. redis.call('TTL', key) .. ' s')
end
if #result == 0 then
  return 'no sessions'
end
return result
