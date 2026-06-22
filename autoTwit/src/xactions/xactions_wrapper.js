/**
 * XActions Node.js 包装器
 * 接收 Python 传入的 JSON，调用 XActions，返回结果
 */

import { Scraper } from 'xactions';

async function main() {
  try {
    // 从 stdin 读取 Python 传入的参数
    let inputData = '';
    process.stdin.setEncoding('utf8');

    for await (const chunk of process.stdin) {
      inputData += chunk;
    }

    const { tool, params, authToken } = JSON.parse(inputData);

    // 初始化 Scraper
    const scraper = new Scraper();
    await scraper.login(authToken);

    let result = {};

    // 根据 tool 类型调用对应方法
    switch (tool) {
      case 'scrape_user_tweets':
        const tweets = await scraper.getTweets(params.username, params.count);
        result = { tweets };
        break;

      case 'get_user_profile':
        const profile = await scraper.getProfile(params.username);
        result = { profile };
        break;

      case 'post_tweet':
        const tweetParams = { text: params.text };

        // 如果有图片，先上传图片
        if (params.image_path) {
          const mediaId = await scraper.uploadMedia(params.image_path);
          tweetParams.media = { media_ids: [mediaId] };
        }

        const tweetResult = await scraper.sendTweet(tweetParams.text, tweetParams.media);
        result = { tweet_id: tweetResult?.rest_id, success: true };
        break;

      case 'like_tweet':
        await scraper.likeTweet(params.tweet_id);
        result = { success: true };
        break;

      case 'follow_user':
        await scraper.followUser(params.username);
        result = { success: true };
        break;

      case 'search_tweets':
        const searchResults = await scraper.searchTweets(params.query, params.count);
        result = { tweets: searchResults };
        break;

      default:
        throw new Error(`Unknown tool: ${tool}`);
    }

    // 输出结果到 stdout
    console.log(JSON.stringify(result));

  } catch (error) {
    console.error(JSON.stringify({ error: error.message }));
    process.exit(1);
  }
}

main();
