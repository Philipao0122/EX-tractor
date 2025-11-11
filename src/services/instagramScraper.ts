import axios from 'axios';

type AxiosInstanceType = ReturnType<typeof axios.create>;

type AxiosError = {
  isAxiosError: boolean;
  response?: {
    data?: any;
  };
  message: string;
};

// Use the AxiosError type from axios
interface InstagramApiError extends Error {
  response?: {
    data?: {
      error?: {
        message: string;
      };
    };
  };
  message: string;
}


export interface InstagramScraperOptions {
  apiKey: string;
  baseUrl?: string;
}

export interface InstagramPost {
  id: string;
  caption?: string;
  media_type: 'IMAGE' | 'VIDEO' | 'CAROUSEL_ALBUM';
  media_url: string;
  permalink: string;
  timestamp: string;
  username: string;
}

export interface InstagramResponse {
  data: InstagramPost[];
  paging?: {
    cursors?: {
      before?: string;
      after?: string;
    };
    next?: string;
  };
  error?: {
    message: string;
    type: string;
    code: number;
  };
}

export class InstagramScraper {
  private client: AxiosInstanceType;
  private apiKey: string;

  constructor(options: InstagramScraperOptions) {
    this.apiKey = options.apiKey;
    this.client = axios.create({
      baseURL: options.baseUrl || 'https://instagram-social-api.scraper.tech',
      headers: {
        'Scraper-Key': this.apiKey,
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Get user posts/reels
   * @param username Instagram username, ID, or profile URL
   * @param paginationToken Token for pagination (optional)
   * @param limit Number of items to return (optional)
   */
  async getUserPosts(
    username: string,
    paginationToken?: string,
    limit: number = 10
  ): Promise<InstagramResponse> {
    const params: Record<string, any> = {
      username_or_id_or_url: username,
      url_embed_safe: 'false',
      limit,
    };

    if (paginationToken) {
      params.pagination_token = paginationToken;
    }

    try {
      const response = await this.client.get<InstagramResponse>('/user-posts-reels', { params });
      return response.data;
    } catch (error: unknown) {
      const axiosError = error as AxiosError;
      if (axiosError.isAxiosError) {
        const errorData = axiosError.response?.data as { error?: { message: string } } | undefined;
        const errorMessage = errorData?.error?.message || axiosError.message;
        throw new Error(`Instagram API error: ${errorMessage}`);
      }
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      throw new Error(errorMessage);
    }
  }

  /**
   * Get all user posts (with pagination)
   * @param username Instagram username, ID, or profile URL
   * @param maxPosts Maximum number of posts to fetch (optional)
   */
  async getAllUserPosts(username: string, maxPosts: number = 100): Promise<InstagramPost[]> {
    let allPosts: InstagramPost[] = [];
    let paginationToken: string | undefined;
    let hasMore = true;

    while (hasMore && allPosts.length < maxPosts) {
      const response = await this.getUserPosts(
        username,
        paginationToken,
        Math.min(50, maxPosts - allPosts.length)
      );

      if (response.data && response.data.length > 0) {
        allPosts = [...allPosts, ...response.data];
      }

      if (response.paging?.next && response.paging?.cursors?.after) {
        paginationToken = response.paging.cursors.after;
      } else {
        hasMore = false;
      }

      // Add a small delay to avoid rate limiting
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }

    return allPosts.slice(0, maxPosts);
  }
}

// Example usage:
/*
const scraper = new InstagramScraper({
  apiKey: 'your_scraper_key_here',
});

// Get first page of posts
const firstPage = await scraper.getUserPosts('username');

// Get all posts (with pagination)
const allPosts = await scraper.getAllUserPosts('username', 50);
*/
